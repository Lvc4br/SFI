import pytest

@pytest.fixture
def client(test_client):
    return test_client


def test_transfer_reversal_compensates_both_accounts_atomically(client):
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": "transfer-reversal@example.com", "password": "senha-forte-teste-123"},
    )
    headers = {"Authorization": f"Bearer {registered.json()['access_token']}"}

    source = client.post(
        "/api/v1/finance/accounts",
        headers=headers,
        json={
            "name": "Conta origem",
            "account_type": "checking",
            "opening_balance": "1000.00",
        },
    )
    destination = client.post(
        "/api/v1/finance/accounts",
        headers=headers,
        json={
            "name": "Conta destino",
            "account_type": "savings",
            "opening_balance": "100.00",
        },
    )
    transfer = client.post(
        "/api/v1/finance/transfers",
        headers=headers,
        json={
            "source_account_id": source.json()["id"],
            "destination_account_id": destination.json()["id"],
            "amount": "125.50",
            "description": "Transferência entre contas",
            "idempotency_key": "paired-transfer-create-001",
        },
    )
    assert transfer.status_code == 201

    reversal = client.post(
        f"/api/v1/finance/transfers/{transfer.json()['id']}/reverse",
        headers=headers,
        params={"idempotency_key": "paired-transfer-reversal-001"},
    )
    assert reversal.status_code == 201
    assert len(reversal.json()["reversal_transactions"]) == 2

    source_balance = client.get(
        f"/api/v1/finance/accounts/{source.json()['id']}/balance",
        headers=headers,
    )
    destination_balance = client.get(
        f"/api/v1/finance/accounts/{destination.json()['id']}/balance",
        headers=headers,
    )
    assert source_balance.json()["balance"] == "1000.00"
    assert destination_balance.json()["balance"] == "100.00"

    history = client.get("/api/v1/finance/transfers", headers=headers)
    assert history.status_code == 200
    assert len(history.json()) == 1
    assert history.json()[0]["is_reversed"] is True
    assert history.json()[0]["reversal_id"] == reversal.json()["reversal_id"]
    assert history.json()[0]["reversed_at"] is not None

    duplicate = client.post(
        f"/api/v1/finance/transfers/{transfer.json()['id']}/reverse",
        headers=headers,
        params={"idempotency_key": "paired-transfer-reversal-002"},
    )
    assert duplicate.status_code == 409

    transactions = client.get("/api/v1/finance/transactions", headers=headers)
    assert transactions.status_code == 200
    assert len(transactions.json()) == 4


def test_transfer_legs_and_reversal_legs_cannot_be_reversed_individually(client):
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "email": "transfer-no-single-reversal@example.com",
            "password": "senha-forte-teste-123",
        },
    )
    headers = {"Authorization": f"Bearer {registered.json()['access_token']}"}
    source = client.post(
        "/api/v1/finance/accounts",
        headers=headers,
        json={"name": "Origem", "account_type": "checking"},
    )
    destination = client.post(
        "/api/v1/finance/accounts",
        headers=headers,
        json={"name": "Destino", "account_type": "savings"},
    )
    transfer = client.post(
        "/api/v1/finance/transfers",
        headers=headers,
        json={
            "source_account_id": source.json()["id"],
            "destination_account_id": destination.json()["id"],
            "amount": "10.00",
            "description": "Transferência",
            "idempotency_key": "paired-transfer-create-002",
        },
    )
    client.post(
        f"/api/v1/finance/transfers/{transfer.json()['id']}/reverse",
        headers=headers,
        params={"idempotency_key": "paired-transfer-reversal-003"},
    )
    transactions = client.get("/api/v1/finance/transactions", headers=headers).json()

    for transaction in transactions:
        response = client.post(
            f"/api/v1/finance/transactions/{transaction['id']}/reverse",
            headers=headers,
            params={"idempotency_key": f"single-reverse-{transaction['id']}"},
        )
        assert response.status_code == 422


def test_transfer_reversal_is_hidden_from_other_users(client):
    owner = client.post(
        "/api/v1/auth/register",
        json={"email": "transfer-owner@example.com", "password": "senha-forte-teste-123"},
    )
    other = client.post(
        "/api/v1/auth/register",
        json={"email": "transfer-other@example.com", "password": "senha-forte-teste-123"},
    )
    owner_headers = {"Authorization": f"Bearer {owner.json()['access_token']}"}
    other_headers = {"Authorization": f"Bearer {other.json()['access_token']}"}

    source = client.post(
        "/api/v1/finance/accounts",
        headers=owner_headers,
        json={"name": "Origem", "account_type": "checking"},
    )
    destination = client.post(
        "/api/v1/finance/accounts",
        headers=owner_headers,
        json={"name": "Destino", "account_type": "savings"},
    )
    transfer = client.post(
        "/api/v1/finance/transfers",
        headers=owner_headers,
        json={
            "source_account_id": source.json()["id"],
            "destination_account_id": destination.json()["id"],
            "amount": "20.00",
            "description": "Transferência privada",
            "idempotency_key": "paired-transfer-create-003",
        },
    )

    hidden = client.post(
        f"/api/v1/finance/transfers/{transfer.json()['id']}/reverse",
        headers=other_headers,
        params={"idempotency_key": "foreign-transfer-reversal-001"},
    )
    assert hidden.status_code == 404
