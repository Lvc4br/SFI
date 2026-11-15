import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from sfi_api.config import Settings
from sfi_api.database import get_session
from sfi_api.main import app
from sfi_api.models import Base


@pytest.fixture
def client(tmp_path, monkeypatch):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'shopping.db'}")
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def prepare():
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(prepare())

    async def override_session():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    monkeypatch.setattr(
        "sfi_api.security.get_settings",
        lambda: Settings(jwt_secret_key="test-only-secret-key-with-at-least-32-bytes"),
    )
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


def register(client, email):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "senha-forte-teste-123"},
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_shopping_lists_items_favorites_and_user_isolation(client):
    owner = register(client, "shopping-owner@example.com")
    other = register(client, "shopping-other@example.com")

    created = client.post(
        "/api/v1/shopping/lists",
        headers=owner,
        json={"name": "Mercado da semana", "is_favorite": True},
    )
    assert created.status_code == 201, created.text
    list_id = created.json()["id"]

    favorite_lists = client.get("/api/v1/shopping/lists?favorites_only=true", headers=owner)
    assert favorite_lists.status_code == 200
    assert len(favorite_lists.json()) == 1

    item = client.post(
        f"/api/v1/shopping/lists/{list_id}/items",
        headers=owner,
        json={"name": "Arroz", "quantity": "2.000", "unit": "kg", "unit_price": "7.50"},
    )
    assert item.status_code == 201, item.text
    assert item.json()["quantity"] == "2.000"

    checked = client.patch(
        f"/api/v1/shopping/lists/{list_id}/items/{item.json()['id']}",
        headers=owner,
        json={"is_checked": True},
    )
    assert checked.status_code == 200
    assert checked.json()["is_checked"] is True

    detail = client.get(f"/api/v1/shopping/lists/{list_id}", headers=owner)
    assert detail.status_code == 200
    assert len(detail.json()["items"]) == 1

    assert client.get("/api/v1/shopping/lists", headers=other).json() == []
    assert client.get(f"/api/v1/shopping/lists/{list_id}", headers=other).status_code == 404
    assert client.patch(
        f"/api/v1/shopping/lists/{list_id}/items/{item.json()['id']}",
        headers=other,
        json={"is_checked": False},
    ).status_code == 404


def test_shopping_rejects_invalid_item_values(client):
    headers = register(client, "shopping-invalid@example.com")
    shopping_list = client.post(
        "/api/v1/shopping/lists", headers=headers, json={"name": "Farmácia"}
    ).json()
    response = client.post(
        f"/api/v1/shopping/lists/{shopping_list['id']}/items",
        headers=headers,
        json={"name": "Vitamina", "quantity": "0", "unit_price": "-1"},
    )
    assert response.status_code == 422



def test_shopping_rejects_null_required_item_fields(client):
    headers = register(client, "shopping-null@example.com")
    shopping_list = client.post(
        "/api/v1/shopping/lists", headers=headers, json={"name": "Mercado"}
    ).json()
    item = client.post(
        f"/api/v1/shopping/lists/{shopping_list['id']}/items",
        headers=headers,
        json={"name": "Leite"},
    ).json()

    for field in ("name", "quantity", "unit", "is_checked", "position"):
        response = client.patch(
            f"/api/v1/shopping/lists/{shopping_list['id']}/items/{item['id']}",
            headers=headers,
            json={field: None},
        )
        assert response.status_code == 422, (field, response.text)


def test_catalog_products_can_be_reused_in_templates_and_copied_lists(client):
    owner = register(client, "shopping-template-owner@example.com")
    other = register(client, "shopping-template-other@example.com")

    product = client.post(
        "/api/v1/shopping/products",
        headers=owner,
        json={"name": "Café em pó", "unit": "pacote"},
    )
    assert product.status_code == 201, product.text
    product_id = product.json()["id"]

    template = client.post(
        "/api/v1/shopping/lists",
        headers=owner,
        json={"name": "Compra mensal", "is_favorite": True, "is_template": True},
    )
    assert template.status_code == 201, template.text
    template_id = template.json()["id"]
    assert template.json()["is_template"] is True

    item = client.post(
        f"/api/v1/shopping/lists/{template_id}/items",
        headers=owner,
        json={
            "name": "Café em pó",
            "product_id": product_id,
            "quantity": "2.000",
            "unit": "pacote",
            "unit_price": "18.90",
        },
    )
    assert item.status_code == 201, item.text
    assert item.json()["product_id"] == product_id

    copied = client.post(
        f"/api/v1/shopping/lists/from-template/{template_id}",
        headers=owner,
    )
    assert copied.status_code == 201, copied.text
    assert copied.json()["is_template"] is False
    assert copied.json()["name"] == "Compra mensal"
    assert len(copied.json()["items"]) == 1
    copied_item = copied.json()["items"][0]
    assert copied_item["product_id"] == product_id
    assert copied_item["is_checked"] is False
    assert copied_item["quantity"] == "2.000"

    assert client.post(
        f"/api/v1/shopping/lists/{template_id}/items",
        headers=other,
        json={"name": "Produto de outro usuário", "product_id": product_id},
    ).status_code == 404


def test_template_creation_rejects_non_template_and_archived_product(client):
    headers = register(client, "shopping-template-validation@example.com")
    ordinary = client.post(
        "/api/v1/shopping/lists", headers=headers, json={"name": "Lista normal"}
    ).json()
    response = client.post(
        f"/api/v1/shopping/lists/from-template/{ordinary['id']}", headers=headers
    )
    assert response.status_code == 409

    product = client.post(
        "/api/v1/shopping/products", headers=headers, json={"name": "Produto arquivado"}
    ).json()
    archived = client.post(
        f"/api/v1/shopping/products/{product['id']}/archive", headers=headers
    )
    assert archived.status_code == 200

    template = client.post(
        "/api/v1/shopping/lists",
        headers=headers,
        json={"name": "Modelo", "is_template": True},
    ).json()
    rejected = client.post(
        f"/api/v1/shopping/lists/{template['id']}/items",
        headers=headers,
        json={"name": "Produto arquivado", "product_id": product["id"]},
    )
    assert rejected.status_code == 404



def test_confirm_purchase_creates_one_expense_and_price_history(client):
    headers = register(client, "shopping-confirm@example.com")
    account = client.post(
        "/api/v1/finance/accounts",
        headers=headers,
        json={"name": "Carteira", "account_type": "cash", "currency": "BRL"},
    )
    assert account.status_code == 201, account.text
    product = client.post(
        "/api/v1/shopping/products",
        headers=headers,
        json={"name": "Arroz", "unit": "kg"},
    )
    assert product.status_code == 201, product.text
    shopping_list = client.post(
        "/api/v1/shopping/lists",
        headers=headers,
        json={"name": "Mercado da semana"},
    )
    list_id = shopping_list.json()["id"]
    item = client.post(
        f"/api/v1/shopping/lists/{list_id}/items",
        headers=headers,
        json={
            "name": "Arroz",
            "product_id": product.json()["id"],
            "quantity": "2.000",
            "unit": "kg",
            "unit_price": "7.50",
        },
    )
    assert item.status_code == 201, item.text

    confirmed = client.post(
        f"/api/v1/shopping/purchases/{list_id}/confirm",
        headers=headers,
        json={"account_id": account.json()["id"], "merchant": "Mercado Central"},
    )
    assert confirmed.status_code == 201, confirmed.text
    assert confirmed.json()["amount"] == "15.00"
    assert confirmed.json()["items_count"] == 1

    transactions = client.get("/api/v1/finance/transactions?limit=100", headers=headers)
    assert transactions.status_code == 200, transactions.text
    purchases = [row for row in transactions.json() if row["description"].startswith("Compra:")]
    assert len(purchases) == 1
    assert purchases[0]["transaction_type"] == "expense"
    assert purchases[0]["amount"] == "15.00"

    prices = client.get(
        f"/api/v1/shopping/products/{product.json()['id']}/prices",
        headers=headers,
    )
    assert prices.status_code == 200, prices.text
    assert len(prices.json()) == 1
    assert prices.json()[0]["price"] == "7.50"
    assert prices.json()[0]["merchant"] == "Mercado Central"

    replay = client.post(
        f"/api/v1/shopping/purchases/{list_id}/confirm",
        headers=headers,
        json={"account_id": account.json()["id"]},
    )
    assert replay.status_code == 409


def test_confirm_purchase_requires_prices(client):
    owner = register(client, "shopping-confirm-owner@example.com")
    other = register(client, "shopping-confirm-other@example.com")
    account = client.post(
        "/api/v1/finance/accounts",
        headers=other,
        json={"name": "Conta alheia", "account_type": "checking", "currency": "BRL"},
    ).json()
    shopping_list = client.post(
        "/api/v1/shopping/lists",
        headers=owner,
        json={"name": "Compra sem preço"},
    ).json()
    client.post(
        f"/api/v1/shopping/lists/{shopping_list['id']}/items",
        headers=owner,
        json={"name": "Produto sem preço"},
    )
    response = client.post(
        f"/api/v1/shopping/purchases/{shopping_list['id']}/confirm",
        headers=owner,
        json={"account_id": account["id"]},
    )
    assert response.status_code == 422
