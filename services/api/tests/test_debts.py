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
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'debts.db'}")
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
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_debt(client, headers):
    response = client.post(
        "/api/v1/debts",
        headers=headers,
        json={
            "creditor": "Banco Exemplo",
            "debt_type": "vehicle",
            "description": "Financiamento do veículo",
            "original_amount": "30000.00",
            "annual_interest_rate": "12.500000",
            "amortization_method": "sac",
            "contracted_at": "2026-01-10",
            "first_due_date": "2026-02-10",
            "installment_count": 36,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_debt_registration_payment_ledger_and_idempotency(client):
    headers = register(client, "debt-owner@example.com")
    account = client.post(
        "/api/v1/finance/accounts",
        headers=headers,
        json={"name": "Conta corrente", "account_type": "checking"},
    ).json()
    debt = create_debt(client, headers)
    assert debt["outstanding_principal"] == "30000.00"
    assert debt["next_due_date"] == "2026-02-10"

    payload = {
        "source_account_id": account["id"],
        "principal_amount": "750.00",
        "interest_amount": "120.50",
        "paid_at": "2026-02-10T12:00:00-03:00",
        "next_due_date": "2026-03-10",
        "idempotency_key": "debt-payment-first-0001",
    }
    url = f"/api/v1/debts/{debt['id']}/payments"
    payment = client.post(url, headers=headers, json=payload)
    assert payment.status_code == 201, payment.text
    assert payment.json()["amount"] == "870.50"
    assert payment.json()["principal_amount"] == "750.00"
    assert payment.json()["interest_amount"] == "120.50"

    replay = client.post(url, headers=headers, json=payload)
    assert replay.status_code == 409

    listed = client.get("/api/v1/debts", headers=headers)
    assert listed.status_code == 200
    assert listed.json()[0]["outstanding_principal"] == "29250.00"
    assert listed.json()[0]["next_due_date"] == "2026-03-10"

    payments = client.get(f"/api/v1/debts/{debt['id']}/payments", headers=headers)
    assert payments.status_code == 200
    assert len(payments.json()) == 1

    transactions = client.get("/api/v1/finance/transactions?limit=100", headers=headers)
    debt_expenses = [
        item for item in transactions.json()
        if item["description"] == "Pagamento de dívida: Financiamento do veículo"
    ]
    assert len(debt_expenses) == 1
    assert debt_expenses[0]["amount"] == "870.50"


def test_debt_payment_rejects_foreign_account_and_overpayment(client):
    owner = register(client, "debt-private-owner@example.com")
    other = register(client, "debt-private-other@example.com")
    foreign_account = client.post(
        "/api/v1/finance/accounts",
        headers=other,
        json={"name": "Conta privada", "account_type": "checking"},
    ).json()
    debt = create_debt(client, owner)
    url = f"/api/v1/debts/{debt['id']}/payments"
    base = {
        "principal_amount": "100.00",
        "interest_amount": "0.00",
        "paid_at": "2026-02-10T12:00:00Z",
        "idempotency_key": "debt-payment-foreign-0001",
    }
    foreign = client.post(
        url, headers=owner, json={**base, "source_account_id": foreign_account["id"]}
    )
    assert foreign.status_code == 404

    own_account = client.post(
        "/api/v1/finance/accounts",
        headers=owner,
        json={"name": "Conta", "account_type": "checking"},
    ).json()
    excessive = client.post(
        url,
        headers=owner,
        json={
            **base,
            "source_account_id": own_account["id"],
            "principal_amount": "30000.01",
        },
    )
    assert excessive.status_code == 422

    assert client.get(f"/api/v1/debts/{debt['id']}/payments", headers=other).status_code == 404


def test_debt_is_marked_paid_when_principal_reaches_zero(client):
    headers = register(client, "debt-paid@example.com")
    account = client.post(
        "/api/v1/finance/accounts",
        headers=headers,
        json={"name": "Conta", "account_type": "checking"},
    ).json()
    debt = client.post(
        "/api/v1/debts",
        headers=headers,
        json={
            "creditor": "Credor",
            "description": "Empréstimo",
            "original_amount": "1000.00",
            "contracted_at": "2026-01-01",
            "first_due_date": "2026-02-01",
        },
    ).json()
    paid = client.post(
        f"/api/v1/debts/{debt['id']}/payments",
        headers=headers,
        json={
            "source_account_id": account["id"],
            "principal_amount": "1000.00",
            "interest_amount": "0.00",
            "paid_at": "2026-02-01T12:00:00Z",
            "idempotency_key": "debt-payment-final-0001",
        },
    )
    assert paid.status_code == 201, paid.text
    updated = client.get("/api/v1/debts", headers=headers).json()[0]
    assert updated["outstanding_principal"] == "0.00"
    assert updated["status"] == "paid"
    assert updated["next_due_date"] is None



@pytest.mark.parametrize(
    ("method", "expected_first_principal"),
    [("price", "825.06"), ("sac", "833.33")],
)
def test_debt_amortization_schedule_is_estimated_and_balances_to_zero(
    client, method, expected_first_principal
):
    headers = register(client, f"debt-schedule-{method}@example.com")
    payload = {
        "creditor": "Banco Exemplo", "debt_type": "loan",
        "description": "Empréstimo de teste", "original_amount": "2500.00",
        "annual_interest_rate": "12.000000", "amortization_method": method,
        "contracted_at": "2026-01-01", "first_due_date": "2026-02-28",
        "installment_count": 3,
    }
    created = client.post("/api/v1/debts", headers=headers, json=payload)
    assert created.status_code == 201, created.text
    response = client.get(f"/api/v1/debts/{created.json()['id']}/schedule", headers=headers)
    assert response.status_code == 200, response.text
    schedule = response.json()
    assert schedule["is_estimate"] is True
    assert len(schedule["installments"]) == 3
    assert schedule["installments"][0]["due_date"] == "2026-02-28"
    assert schedule["installments"][-1]["due_date"] == "2026-04-28"
    assert schedule["installments"][0]["principal"] == expected_first_principal
    assert schedule["installments"][-1]["closing_balance"] == "0.00"
    assert schedule["principal_total"] == "2500.00"
    assert float(schedule["interest_total"]) > 0


def test_debt_schedule_rejects_manual_method_and_hides_foreign_debt(client):
    owner = register(client, "debt-schedule-owner@example.com")
    other = register(client, "debt-schedule-other@example.com")
    manual = client.post("/api/v1/debts", headers=owner, json={
        "creditor": "Credor", "description": "Manual", "original_amount": "1000.00",
        "contracted_at": "2026-01-01", "first_due_date": "2026-02-01",
    }).json()
    assert client.get(f"/api/v1/debts/{manual['id']}/schedule", headers=owner).status_code == 409
    assert client.get(f"/api/v1/debts/{manual['id']}/schedule", headers=other).status_code == 404


def test_debt_schedule_supports_zero_interest_and_month_end_dates(client):
    headers = register(client, "debt-schedule-zero@example.com")
    created = client.post("/api/v1/debts", headers=headers, json={
        "creditor": "Credor", "description": "Sem juros", "original_amount": "100.00",
        "annual_interest_rate": "0", "amortization_method": "price",
        "contracted_at": "2026-01-01", "first_due_date": "2026-01-31",
        "installment_count": 3,
    })
    assert created.status_code == 201, created.text
    schedule = client.get(f"/api/v1/debts/{created.json()['id']}/schedule", headers=headers).json()
    assert schedule["interest_total"] == "0.00"
    assert schedule["payment_total"] == "100.00"
    assert [item["due_date"] for item in schedule["installments"]] == [
        "2026-01-31", "2026-02-28", "2026-03-31"
    ]
    invalid = client.post("/api/v1/debts", headers=headers, json={
        "creditor": "Credor", "description": "Excesso", "original_amount": "100.00",
        "contracted_at": "2026-01-01", "first_due_date": "2026-02-01",
        "installment_count": 601,
    })
    assert invalid.status_code == 422
