import pytest

@pytest.fixture
def client(test_client):
    return test_client


def test_monthly_recurrence_forecast_clamps_month_end_without_creating_transactions(client):
    token_response = client.post(
        "/api/v1/auth/register",
        json={"email": "recurrence-owner@example.com", "password": "senha-forte-teste-123"},
    )
    assert token_response.status_code == 201
    headers = {"Authorization": f"Bearer {token_response.json()['access_token']}"}

    account = client.post(
        "/api/v1/finance/accounts",
        headers=headers,
        json={
            "name": "Conta recorrente",
            "account_type": "checking",
            "opening_balance": "500.00",
        },
    )
    assert account.status_code == 201
    category = client.post(
        "/api/v1/finance/categories",
        headers=headers,
        json={"name": "Aluguel", "category_type": "expense"},
    )
    assert category.status_code == 201

    recurrence = client.post(
        "/api/v1/finance/recurrences",
        headers=headers,
        json={
            "account_id": account.json()["id"],
            "category_id": category.json()["id"],
            "transaction_type": "expense",
            "amount": "1200.00",
            "description": "Aluguel mensal",
            "idempotency_key": "recurrence-rent-2027-001",
            "frequency": "monthly",
            "start_date": "2027-01-31",
        },
    )
    assert recurrence.status_code == 201

    forecast = client.get(
        "/api/v1/finance/cash-flow/forecast"
        "?start_date=2027-01-01&end_date=2027-03-31",
        headers=headers,
    )
    assert forecast.status_code == 200
    body = forecast.json()
    assert [item["due_date"] for item in body["occurrences"]] == [
        "2027-01-31",
        "2027-02-28",
        "2027-03-31",
    ]
    assert body["totals_by_currency"] == [
        {
            "currency": "BRL",
            "income_total": "0.00",
            "expense_total": "3600.00",
            "net_flow": "-3600.00",
        }
    ]

    transactions = client.get("/api/v1/finance/transactions", headers=headers)
    balance = client.get(
        f"/api/v1/finance/accounts/{account.json()['id']}/balance",
        headers=headers,
    )
    assert transactions.status_code == 200
    assert transactions.json() == []
    assert balance.status_code == 200
    assert balance.json()["balance"] == "500.00"


def test_recurrence_pause_excludes_it_from_forecast(client):
    token_response = client.post(
        "/api/v1/auth/register",
        json={"email": "recurrence-pause@example.com", "password": "senha-forte-teste-123"},
    )
    headers = {"Authorization": f"Bearer {token_response.json()['access_token']}"}
    account = client.post(
        "/api/v1/finance/accounts",
        headers=headers,
        json={"name": "Conta", "account_type": "checking"},
    )
    recurrence = client.post(
        "/api/v1/finance/recurrences",
        headers=headers,
        json={
            "account_id": account.json()["id"],
            "transaction_type": "income",
            "amount": "250.00",
            "description": "Pagamento",
            "idempotency_key": "recurrence-pay-2027-001",
            "frequency": "weekly",
            "start_date": "2027-01-01",
        },
    )
    assert recurrence.status_code == 201

    paused = client.patch(
        f"/api/v1/finance/recurrences/{recurrence.json()['id']}",
        headers=headers,
        json={"is_active": False},
    )
    assert paused.status_code == 200
    forecast = client.get(
        "/api/v1/finance/cash-flow/forecast"
        "?start_date=2027-01-01&end_date=2027-01-31",
        headers=headers,
    )
    assert forecast.status_code == 200
    assert forecast.json()["occurrences"] == []
