from fastapi.testclient import TestClient


def _register(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "senha-forte-teste-123"},
    )
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_product_catalog_and_price_history_are_user_scoped(client):
    owner = _register(client, "product-owner@example.com")
    other = _register(client, "product-other@example.com")

    created = client.post(
        "/api/v1/shopping/products",
        headers=owner,
        json={"name": "Arroz integral", "brand": "Marca teste", "unit": "kg"},
    )
    assert created.status_code == 201, created.text
    product_id = created.json()["id"]

    price = client.post(
        f"/api/v1/shopping/products/{product_id}/prices",
        headers=owner,
        json={
            "price": "12.90",
            "currency": "BRL",
            "merchant": "Mercado fictício",
            "source": "manual",
            "observed_at": "2026-11-15T10:00:00Z",
        },
    )
    assert price.status_code == 201, price.text
    assert price.json()["price"] == "12.90"

    history = client.get(
        f"/api/v1/shopping/products/{product_id}/prices", headers=owner
    )
    assert history.status_code == 200
    assert len(history.json()) == 1

    assert client.get("/api/v1/shopping/products", headers=other).json() == []
    assert client.get(
        f"/api/v1/shopping/products/{product_id}/prices", headers=other
    ).status_code == 404


def test_product_search_and_archive(client):
    owner = _register(client, "product-archive@example.com")
    created = client.post(
        "/api/v1/shopping/products",
        headers=owner,
        json={"name": "Leite sem lactose"},
    )
    product_id = created.json()["id"]

    assert len(client.get(
        "/api/v1/shopping/products?search=sem%20lactose", headers=owner
    ).json()) == 1
    archived = client.post(
        f"/api/v1/shopping/products/{product_id}/archive", headers=owner
    )
    assert archived.status_code == 200
    assert client.get("/api/v1/shopping/products", headers=owner).json() == []
