import asyncio
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from sfi_api.config import Settings
from sfi_api.database import get_session
from sfi_api.main import app
from sfi_api.models import Base
from sfi_api.schemas.finance import TransactionCreate


@pytest.fixture
def client(tmp_path, monkeypatch):
    database_path = tmp_path / "sfi-finance-test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}")
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def prepare_database():
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(prepare_database())

    async def override_session():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session

    def test_settings() -> Settings:
        return Settings(jwt_secret_key="test-only-secret-key-with-at-least-32-bytes")

    monkeypatch.setattr("sfi_api.security.get_settings", test_settings)

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


def register(client: TestClient, email: str) -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "senha-forte-teste-123"},
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def test_account_category_and_transaction_flow(client):
    token = register(client, "owner@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    account = client.post(
        "/api/v1/finance/accounts",
        headers=headers,
        json={"name": "Conta principal", "account_type": "checking", "opening_balance": "1000.00"},
    )
    assert account.status_code == 201
    account_id = account.json()["id"]

    category = client.post(
        "/api/v1/finance/categories",
        headers=headers,
        json={"name": "Moradia", "category_type": "expense"},
    )
    assert category.status_code == 201

    transaction = client.post(
        "/api/v1/finance/transactions",
        headers=headers,
        json={
            "account_id": account_id,
            "category_id": category.json()["id"],
            "transaction_type": "expense",
            "amount": "125.90",
            "description": "Conta de energia",
            "occurred_at": datetime.now(UTC).isoformat(),
            "idempotency_key": "finance-test-key-0001",
        },
    )
    assert transaction.status_code == 201
    assert transaction.json()["amount"] == "125.90"
    assert transaction.json()["currency"] == "BRL"

    listing = client.get("/api/v1/finance/transactions", headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1


def test_financial_data_is_isolated_between_users(client):
    owner_token = register(client, "owner2@example.com")
    other_token = register(client, "other@example.com")

    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    other_headers = {"Authorization": f"Bearer {other_token}"}

    account = client.post(
        "/api/v1/finance/accounts",
        headers=owner_headers,
        json={"name": "Conta privada", "account_type": "checking"},
    )
    account_id = account.json()["id"]

    assert client.get("/api/v1/finance/accounts", headers=other_headers).json() == []
    foreign_transaction = client.post(
        "/api/v1/finance/transactions",
        headers=other_headers,
        json={
            "account_id": account_id,
            "transaction_type": "expense",
            "amount": "1.00",
            "description": "Tentativa de acesso",
            "idempotency_key": "foreign-user-key-001",
        },
    )
    assert foreign_transaction.status_code == 404


def test_transactions_reject_duplicate_idempotency_key(client):
    token = register(client, "idem@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    account = client.post(
        "/api/v1/finance/accounts",
        headers=headers,
        json={"name": "Carteira", "account_type": "cash"},
    )
    payload = {
        "account_id": account.json()["id"],
        "transaction_type": "income",
        "amount": "250.00",
        "description": "Pagamento",
        "idempotency_key": "same-key-finance-0001",
    }
    first = client.post("/api/v1/finance/transactions", headers=headers, json=payload)
    second = client.post("/api/v1/finance/transactions", headers=headers, json=payload)
    assert first.status_code == 201
    assert second.status_code == 409


def test_transactions_are_append_only(client):
    token = register(client, "append@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    account = client.post(
        "/api/v1/finance/accounts",
        headers=headers,
        json={"name": "Conta", "account_type": "checking"},
    )
    created = client.post(
        "/api/v1/finance/transactions",
        headers=headers,
        json={
            "account_id": account.json()["id"],
            "transaction_type": "income",
            "amount": "300.00",
            "description": "Salário",
            "idempotency_key": "append-only-key-0001",
        },
    )
    assert created.status_code == 201
    assert client.patch(
        f"/api/v1/finance/transactions/{created.json()['id']}",
        headers=headers,
        json={"amount": "999.99"},
    ).status_code == 404


def test_account_balance_and_summary_are_calculated_with_decimal(client):
    token = register(client, "summary@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    account = client.post(
        "/api/v1/finance/accounts",
        headers=headers,
        json={"name": "Conta principal", "account_type": "checking", "opening_balance": "1000.00"},
    )
    account_id = account.json()["id"]
    category = client.post(
        "/api/v1/finance/categories",
        headers=headers,
        json={"name": "Mercado", "category_type": "expense"},
    )
    for transaction_type, amount, key in [
        ("income", "250.10", "summary-income-key-0001"),
        ("expense", "49.99", "summary-expense-key-0001"),
    ]:
        response = client.post(
            "/api/v1/finance/transactions",
            headers=headers,
            json={
                "account_id": account_id,
                "category_id": category.json()["id"] if transaction_type == "expense" else None,
                "transaction_type": transaction_type,
                "amount": amount,
                "description": "Movimentação de teste",
                "occurred_at": "2026-11-10T12:00:00+00:00",
                "idempotency_key": key,
            },
        )
        assert response.status_code == 201

    balance = client.get(f"/api/v1/finance/accounts/{account_id}/balance", headers=headers)
    assert balance.status_code == 200
    assert balance.json()["balance"] == "1200.11"
    assert balance.json()["balance_kind"] == "available_balance"

    summary = client.get(
        "/api/v1/finance/summary?start_date=2026-11-01&end_date=2026-11-30",
        headers=headers,
    )
    assert summary.status_code == 200
    assert summary.json()["totals_by_currency"] == [
        {
            "currency": "BRL",
            "income_total": "250.10",
            "expense_total": "49.99",
            "net_flow": "200.11",
        }
    ]
    assert summary.json()["spending_by_category"][0]["amount"] == "49.99"


def test_credit_balance_is_reported_as_used_credit_not_cash(client):
    token = register(client, "credit-summary@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    account = client.post(
        "/api/v1/finance/accounts",
        headers=headers,
        json={"name": "Cartão", "account_type": "credit"},
    )
    transaction = client.post(
        "/api/v1/finance/transactions",
        headers=headers,
        json={
            "account_id": account.json()["id"],
            "transaction_type": "expense",
            "amount": "89.90",
            "description": "Compra no cartão",
            "idempotency_key": "credit-summary-key-0001",
        },
    )
    assert transaction.status_code == 201
    balance = client.get(
        f"/api/v1/finance/accounts/{account.json()['id']}/balance",
        headers=headers,
    )
    assert balance.status_code == 200
    assert balance.json()["balance"] == "89.90"
    assert balance.json()["balance_kind"] == "credit_used"


def test_summary_rejects_invalid_period(client):
    token = register(client, "period@example.com")
    response = client.get(
        "/api/v1/finance/summary?start_date=2026-12-01&end_date=2026-11-01",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


def test_monthly_budget_tracks_spending_and_remaining_amount(client):
    token = register(client, "budget@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    account = client.post(
        "/api/v1/finance/accounts",
        headers=headers,
        json={"name": "Conta", "account_type": "checking"},
    )
    category = client.post(
        "/api/v1/finance/categories",
        headers=headers,
        json={"name": "Mercado", "category_type": "expense"},
    )
    transaction = client.post(
        "/api/v1/finance/transactions",
        headers=headers,
        json={
            "account_id": account.json()["id"],
            "category_id": category.json()["id"],
            "transaction_type": "expense",
            "amount": "125.50",
            "description": "Compra mensal",
            "occurred_at": "2026-11-10T12:00:00+00:00",
            "idempotency_key": "budget-expense-key-0001",
        },
    )
    assert transaction.status_code == 201

    budget = client.post(
        "/api/v1/finance/budgets",
        headers=headers,
        json={
            "category_id": category.json()["id"],
            "period": "2026-11",
            "limit_amount": "200.00",
        },
    )
    assert budget.status_code == 201
    assert budget.json()["spent_amount"] == "125.50"
    assert budget.json()["remaining_amount"] == "74.50"
    assert budget.json()["usage_percent"] == "62.75"
    assert budget.json()["status"] == "within_limit"

    listing = client.get("/api/v1/finance/budgets?period=2026-11", headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1


def test_monthly_budget_enforces_category_ownership_and_uniqueness(client):
    token = register(client, "budget-owner@example.com")
    other_token = register(client, "budget-other@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    other_headers = {"Authorization": f"Bearer {other_token}"}
    category = client.post(
        "/api/v1/finance/categories",
        headers=headers,
        json={"name": "Transporte", "category_type": "expense"},
    )
    payload = {
        "category_id": category.json()["id"],
        "period": "2026-11",
        "limit_amount": "300.00",
    }
    foreign_budget = client.post(
        "/api/v1/finance/budgets", headers=other_headers, json=payload
    )
    assert foreign_budget.status_code == 404
    assert client.post("/api/v1/finance/budgets", headers=headers, json=payload).status_code == 201
    assert client.post("/api/v1/finance/budgets", headers=headers, json=payload).status_code == 409
    assert client.get("/api/v1/finance/budgets?period=2026-11", headers=other_headers).json() == []


def test_transfer_moves_value_between_accounts_without_creating_net_income(client):
    token = register(client, "transfer@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    source = client.post(
        "/api/v1/finance/accounts", headers=headers,
        json={"name": "Conta origem", "account_type": "checking", "opening_balance": "500.00"},
    )
    destination = client.post(
        "/api/v1/finance/accounts", headers=headers,
        json={"name": "Conta destino", "account_type": "savings"},
    )
    payload = {
        "source_account_id": source.json()["id"],
        "destination_account_id": destination.json()["id"],
        "amount": "125.75",
        "description": "Reserva",
        "occurred_at": "2026-11-10T12:00:00+00:00",
        "idempotency_key": "transfer-test-key-0001",
    }
    transfer = client.post("/api/v1/finance/transfers", headers=headers, json=payload)
    assert transfer.status_code == 201
    assert transfer.json()["amount"] == "125.75"
    source_balance = client.get(
        f"/api/v1/finance/accounts/{source.json()['id']}/balance", headers=headers
    )
    destination_balance = client.get(
        f"/api/v1/finance/accounts/{destination.json()['id']}/balance", headers=headers
    )
    assert source_balance.json()["balance"] == "374.25"
    assert destination_balance.json()["balance"] == "125.75"
    summary = client.get(
        "/api/v1/finance/summary?start_date=2026-11-01&end_date=2026-11-30",
        headers=headers,
    )
    assert summary.status_code == 200
    totals = summary.json()["totals_by_currency"][0]
    assert totals["income_total"] == "0.00"
    assert totals["expense_total"] == "0.00"
    assert totals["net_flow"] == "0.00"


def test_transfer_rejects_foreign_accounts_and_duplicate_keys(client):
    token = register(client, "transfer-owner@example.com")
    other_token = register(client, "transfer-other@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    other_headers = {"Authorization": f"Bearer {other_token}"}
    source = client.post(
        "/api/v1/finance/accounts", headers=headers,
        json={"name": "Origem", "account_type": "checking"},
    )
    foreign = client.post(
        "/api/v1/finance/accounts", headers=other_headers,
        json={"name": "Alheia", "account_type": "checking"},
    )
    payload = {
        "source_account_id": source.json()["id"],
        "destination_account_id": foreign.json()["id"],
        "amount": "10.00",
        "description": "Teste",
        "idempotency_key": "transfer-owner-key-001",
    }
    foreign_transfer = client.post(
        "/api/v1/finance/transfers", headers=headers, json=payload
    )
    assert foreign_transfer.status_code == 404
    own_destination = client.post(
        "/api/v1/finance/accounts", headers=headers,
        json={"name": "Destino", "account_type": "checking"},
    )
    payload["destination_account_id"] = own_destination.json()["id"]
    first_transfer = client.post(
        "/api/v1/finance/transfers", headers=headers, json=payload
    )
    assert first_transfer.status_code == 201
    duplicate_transfer = client.post(
        "/api/v1/finance/transfers", headers=headers, json=payload
    )
    assert duplicate_transfer.status_code == 409


def test_transaction_reversal_is_compensating_and_cannot_be_repeated(client):
    token = register(client, "reversal@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    account = client.post(
        "/api/v1/finance/accounts", headers=headers,
        json={"name": "Conta", "account_type": "checking"},
    )
    original = client.post(
        "/api/v1/finance/transactions", headers=headers,
        json={
            "account_id": account.json()["id"],
            "transaction_type": "expense",
            "amount": "42.90",
            "description": "Compra",
            "idempotency_key": "reversal-original-key-01",
        },
    )
    assert original.status_code == 201
    reversal = client.post(
        f"/api/v1/finance/transactions/{original.json()['id']}/reverse",
        headers=headers,
        params={"idempotency_key": "reversal-compensate-key-01"},
    )
    assert reversal.status_code == 201
    assert reversal.json()["reversal_transaction"]["transaction_type"] == "income"
    assert reversal.json()["reversal_transaction"]["amount"] == "42.90"
    repeated = client.post(
        f"/api/v1/finance/transactions/{original.json()['id']}/reverse",
        headers=headers,
        params={"idempotency_key": "reversal-compensate-key-02"},
    )
    assert repeated.status_code == 409
    listing = client.get("/api/v1/finance/transactions", headers=headers)
    assert len(listing.json()) == 2


def test_reversal_rejects_transactions_owned_by_another_user(client):
    token = register(client, "reversal-owner@example.com")
    other_token = register(client, "reversal-other@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    other_headers = {"Authorization": f"Bearer {other_token}"}
    account = client.post(
        "/api/v1/finance/accounts", headers=headers,
        json={"name": "Conta", "account_type": "checking"},
    )
    original = client.post(
        "/api/v1/finance/transactions", headers=headers,
        json={
            "account_id": account.json()["id"],
            "transaction_type": "income",
            "amount": "20.00",
            "description": "Crédito",
            "idempotency_key": "reversal-foreign-original",
        },
    )
    response = client.post(
        f"/api/v1/finance/transactions/{original.json()['id']}/reverse",
        headers=other_headers,
        params={"idempotency_key": "reversal-foreign-attempt"},
    )
    assert response.status_code == 404


def test_compensating_transaction_cannot_be_reversed_again(client):
    token = register(client, "double-reversal@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    account = client.post(
        "/api/v1/finance/accounts", headers=headers,
        json={"name": "Conta", "account_type": "checking"},
    )
    original = client.post(
        "/api/v1/finance/transactions", headers=headers,
        json={
            "account_id": account.json()["id"],
            "transaction_type": "expense",
            "amount": "15.00",
            "description": "Despesa original",
            "idempotency_key": "double-reverse-original-001",
        },
    )
    reversal = client.post(
        f"/api/v1/finance/transactions/{original.json()['id']}/reverse",
        headers=headers,
        params={"idempotency_key": "double-reverse-first-001"},
    )
    reversal_id = reversal.json()["reversal_transaction"]["id"]
    second_reversal = client.post(
        f"/api/v1/finance/transactions/{reversal_id}/reverse",
        headers=headers,
        params={"idempotency_key": "double-reverse-second-001"},
    )
    assert second_reversal.status_code == 422


def test_reversed_expense_is_removed_from_budget_and_category_spending(client):
    token = register(client, "budget-reversal@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    account = client.post(
        "/api/v1/finance/accounts",
        headers=headers,
        json={"name": "Conta", "account_type": "checking"},
    ).json()
    category = client.post(
        "/api/v1/finance/categories",
        headers=headers,
        json={"name": "Mercado", "category_type": "expense"},
    ).json()
    transaction = client.post(
        "/api/v1/finance/transactions",
        headers=headers,
        json={
            "account_id": account["id"],
            "category_id": category["id"],
            "transaction_type": "expense",
            "amount": "125.50",
            "description": "Compra estornada",
            "occurred_at": "2026-11-10T12:00:00+00:00",
            "idempotency_key": "budget-reversal-expense-01",
        },
    )
    assert transaction.status_code == 201
    budget = client.post(
        "/api/v1/finance/budgets",
        headers=headers,
        json={
            "category_id": category["id"],
            "period": "2026-11",
            "limit_amount": "200.00",
        },
    )
    assert budget.status_code == 201
    assert budget.json()["spent_amount"] == "125.50"

    reversal = client.post(
        f"/api/v1/finance/transactions/{transaction.json()['id']}/reverse",
        headers=headers,
        params={"idempotency_key": "budget-reversal-key-0001"},
    )
    assert reversal.status_code == 201

    updated_budget = client.get(
        "/api/v1/finance/budgets?period=2026-11", headers=headers
    )
    assert updated_budget.status_code == 200
    assert updated_budget.json()[0]["spent_amount"] == "0.00"
    assert updated_budget.json()[0]["remaining_amount"] == "200.00"

    summary = client.get(
        "/api/v1/finance/summary?start_date=2026-11-01&end_date=2026-11-30",
        headers=headers,
    )
    assert summary.status_code == 200
    assert summary.json()["spending_by_category"] == []


def test_accounts_and_categories_can_be_renamed_and_archived_without_deleting_history(client):
    token = register(client, "archive-finance@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    account = client.post(
        "/api/v1/finance/accounts",
        headers=headers,
        json={"name": "Conta original", "account_type": "checking"},
    ).json()
    category = client.post(
        "/api/v1/finance/categories",
        headers=headers,
        json={"name": "Categoria original", "category_type": "expense"},
    ).json()

    renamed_account = client.patch(
        f"/api/v1/finance/accounts/{account['id']}",
        headers=headers,
        json={"name": "Conta renomeada"},
    )
    assert renamed_account.status_code == 200
    assert renamed_account.json()["name"] == "Conta renomeada"

    renamed_category = client.patch(
        f"/api/v1/finance/categories/{category['id']}",
        headers=headers,
        json={"name": "Categoria renomeada"},
    )
    assert renamed_category.status_code == 200
    assert renamed_category.json()["name"] == "Categoria renomeada"

    archived_category = client.post(
        f"/api/v1/finance/categories/{category['id']}/archive",
        headers=headers,
    )
    assert archived_category.status_code == 200
    assert archived_category.json()["archived_at"] is not None
    assert client.get("/api/v1/finance/categories", headers=headers).json() == []
    archived_categories = client.get(
        "/api/v1/finance/categories?include_archived=true", headers=headers
    ).json()
    assert len(archived_categories) == 1
    assert archived_categories[0]["name"] == "Categoria renomeada"

    archived_category_transaction = client.post(
        "/api/v1/finance/transactions",
        headers=headers,
        json={
            "account_id": account["id"],
            "category_id": category["id"],
            "transaction_type": "expense",
            "amount": "1.00",
            "description": "Categoria arquivada",
            "idempotency_key": "archived-category-key-01",
        },
    )
    assert archived_category_transaction.status_code == 404

    archived_account = client.post(
        f"/api/v1/finance/accounts/{account['id']}/archive",
        headers=headers,
    )
    assert archived_account.status_code == 200
    assert archived_account.json()["archived_at"] is not None
    assert client.get("/api/v1/finance/accounts", headers=headers).json() == []
    archived_accounts = client.get(
        "/api/v1/finance/accounts?include_archived=true", headers=headers
    ).json()
    assert len(archived_accounts) == 1
    assert archived_accounts[0]["name"] == "Conta renomeada"

    archived_account_transaction = client.post(
        "/api/v1/finance/transactions",
        headers=headers,
        json={
            "account_id": account["id"],
            "transaction_type": "income",
            "amount": "1.00",
            "description": "Conta arquivada",
            "idempotency_key": "archived-account-key-001",
        },
    )
    assert archived_account_transaction.status_code == 404


def test_account_with_nonzero_balance_cannot_be_archived(client):
    token = register(client, "archive-nonzero@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    account = client.post(
        "/api/v1/finance/accounts",
        headers=headers,
        json={"name": "Conta com saldo", "account_type": "checking", "opening_balance": "10.00"},
    ).json()

    archived = client.post(
        f"/api/v1/finance/accounts/{account['id']}/archive",
        headers=headers,
    )
    assert archived.status_code == 409
    assert "Zere o saldo" in archived.json()["detail"]


def test_summary_and_monthly_budget_use_user_timezone_boundaries(client):
    token = register(client, "timezone-period@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    account = client.post(
        "/api/v1/finance/accounts",
        headers=headers,
        json={"name": "Conta", "account_type": "checking"},
    ).json()
    category = client.post(
        "/api/v1/finance/categories",
        headers=headers,
        json={"name": "Mercado", "category_type": "expense"},
    ).json()
    transaction = client.post(
        "/api/v1/finance/transactions",
        headers=headers,
        json={
            "account_id": account["id"],
            "category_id": category["id"],
            "transaction_type": "expense",
            "amount": "10.00",
            "description": "Compra próxima da meia-noite",
            "occurred_at": "2026-11-01T02:00:00+00:00",
            "idempotency_key": "timezone-boundary-expense-01",
        },
    )
    assert transaction.status_code == 201

    for period in ("2026-10", "2026-11"):
        created = client.post(
            "/api/v1/finance/budgets",
            headers=headers,
            json={
                "category_id": category["id"],
                "period": period,
                "limit_amount": "100.00",
            },
        )
        assert created.status_code == 201

    october = client.get(
        "/api/v1/finance/budgets?period=2026-10", headers=headers
    ).json()[0]
    november = client.get(
        "/api/v1/finance/budgets?period=2026-11", headers=headers
    ).json()[0]
    assert october["spent_amount"] == "10.00"
    assert november["spent_amount"] == "0.00"

    local_october = client.get(
        "/api/v1/finance/summary?start_date=2026-10-31&end_date=2026-10-31",
        headers=headers,
    ).json()
    local_november = client.get(
        "/api/v1/finance/summary?start_date=2026-11-01&end_date=2026-11-01",
        headers=headers,
    ).json()
    assert local_october["totals_by_currency"][0]["expense_total"] == "10.00"
    assert local_november["totals_by_currency"] == []

    updated_timezone = client.patch(
        "/api/v1/auth/me/timezone",
        headers=headers,
        json={"timezone": "UTC"},
    )
    assert updated_timezone.status_code == 200

    utc_november = client.get(
        "/api/v1/finance/summary?start_date=2026-11-01&end_date=2026-11-01",
        headers=headers,
    ).json()
    assert utc_november["totals_by_currency"][0]["expense_total"] == "10.00"



def test_transaction_amount_preserves_decimal_precision_and_rejects_excess_scale(client):
    # Validate the full Numeric(18, 2) boundary without SQLite persistence:
    # SQLite NUMERIC affinity uses binary floating point for large values,
    # unlike PostgreSQL NUMERIC, and cannot represent every cent at this magnitude.
    boundary_payload = TransactionCreate.model_validate(
        {
            "account_id": "00000000-0000-0000-0000-000000000001",
            "transaction_type": "income",
            "amount": "9999999999999999.99",
            "description": "Limite decimal",
            "idempotency_key": "decimal-limit-accepted-001",
        }
    )
    assert boundary_payload.amount == Decimal("9999999999999999.99")
    with pytest.raises(ValueError):
        TransactionCreate.model_validate(
            {
                "account_id": "00000000-0000-0000-0000-000000000001",
                "transaction_type": "income",
                "amount": "0.001",
                "description": "Escala excedente",
                "idempotency_key": "decimal-excess-scale-001",
            }
        )

    token = register(client, "decimal-boundary@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    account = client.post(
        "/api/v1/finance/accounts",
        headers=headers,
        json={"name": "Conta decimal", "account_type": "checking"},
    )
    assert account.status_code == 201, account.text

    persisted = client.post(
        "/api/v1/finance/transactions",
        headers=headers,
        json={
            "account_id": account.json()["id"],
            "transaction_type": "income",
            "amount": "123456.78",
            "description": "Persistência decimal",
            "idempotency_key": "decimal-persistence-001",
        },
    )
    assert persisted.status_code == 201, persisted.text
    assert persisted.json()["amount"] == "123456.78"


def test_idempotency_keys_are_scoped_to_each_user(client):
    first_token = register(client, "decimal-owner-a@example.com")
    second_token = register(client, "decimal-owner-b@example.com")
    first_headers = {"Authorization": f"Bearer {first_token}"}
    second_headers = {"Authorization": f"Bearer {second_token}"}

    first_account = client.post(
        "/api/v1/finance/accounts",
        headers=first_headers,
        json={"name": "Conta A", "account_type": "checking"},
    )
    second_account = client.post(
        "/api/v1/finance/accounts",
        headers=second_headers,
        json={"name": "Conta B", "account_type": "checking"},
    )
    shared_key = "same-idempotency-key-two-users"

    first = client.post(
        "/api/v1/finance/transactions",
        headers=first_headers,
        json={
            "account_id": first_account.json()["id"],
            "transaction_type": "income",
            "amount": "10.10",
            "description": "Lançamento A",
            "idempotency_key": shared_key,
        },
    )
    second = client.post(
        "/api/v1/finance/transactions",
        headers=second_headers,
        json={
            "account_id": second_account.json()["id"],
            "transaction_type": "income",
            "amount": "10.10",
            "description": "Lançamento B",
            "idempotency_key": shared_key,
        },
    )
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json()["id"] != second.json()["id"]


def test_transaction_requires_timezone_aware_timestamp(client):
    token = register(client, "timezone-required@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    account = client.post(
        "/api/v1/finance/accounts",
        headers=headers,
        json={"name": "Conta timezone", "account_type": "checking"},
    )
    response = client.post(
        "/api/v1/finance/transactions",
        headers=headers,
        json={
            "account_id": account.json()["id"],
            "transaction_type": "expense",
            "amount": "1.00",
            "description": "Data sem timezone",
            "occurred_at": "2026-11-14T12:00:00",
            "idempotency_key": "timezone-missing-offset-001",
        },
    )
    assert response.status_code == 422



def test_financial_summary_keeps_currencies_separate_without_implicit_conversion(client):
    token = register(client, "multi-currency@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    brl = client.post(
        "/api/v1/finance/accounts",
        headers=headers,
        json={"name": "Conta BRL", "account_type": "checking", "currency": "BRL"},
    )
    usd = client.post(
        "/api/v1/finance/accounts",
        headers=headers,
        json={"name": "Conta USD", "account_type": "checking", "currency": "USD"},
    )
    assert brl.status_code == 201
    assert usd.status_code == 201

    for account_id, amount, key in [
        (brl.json()["id"], "100.00", "currency-brl-income-001"),
        (usd.json()["id"], "25.50", "currency-usd-income-001"),
    ]:
        created = client.post(
            "/api/v1/finance/transactions",
            headers=headers,
            json={
                "account_id": account_id,
                "transaction_type": "income",
                "amount": amount,
                "description": "Receita de teste",
                "occurred_at": "2026-11-14T12:00:00+00:00",
                "idempotency_key": key,
            },
        )
        assert created.status_code == 201, created.text

    summary = client.get(
        "/api/v1/finance/summary?start_date=2026-11-01&end_date=2026-11-30",
        headers=headers,
    )
    assert summary.status_code == 200
    totals = {item["currency"]: item for item in summary.json()["totals_by_currency"]}
    assert totals["BRL"]["income_total"] == "100.00"
    assert totals["USD"]["income_total"] == "25.50"
    assert totals["BRL"]["net_flow"] == "100.00"
    assert totals["USD"]["net_flow"] == "25.50"
