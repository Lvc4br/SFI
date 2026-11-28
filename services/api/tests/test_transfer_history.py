def test_transfer_history_is_paginated_and_user_scoped(test_client):
    client = test_client
    first = client.post(
        "/api/v1/auth/register",
        json={
            "email": "transfer-history-owner@example.com",
            "password": "senha-forte-teste-123",
        },
    )
    second = client.post(
        "/api/v1/auth/register",
        json={
            "email": "transfer-history-other@example.com",
            "password": "senha-forte-teste-123",
        },
    )
    owner_headers = {"Authorization": f"Bearer {first.json()['access_token']}"}
    other_headers = {"Authorization": f"Bearer {second.json()['access_token']}"}

    source = client.post(
        "/api/v1/finance/accounts", headers=owner_headers,
        json={"name": "Origem", "account_type": "checking"},
    )
    destination = client.post(
        "/api/v1/finance/accounts", headers=owner_headers,
        json={"name": "Destino", "account_type": "savings"},
    )
    for index in range(2):
        response = client.post(
            "/api/v1/finance/transfers",
            headers=owner_headers,
            json={
                "source_account_id": source.json()["id"],
                "destination_account_id": destination.json()["id"],
                "amount": "10.25",
                "description": f"Transferência {index}",
                "idempotency_key": f"history-transfer-key-{index:04d}",
            },
        )
        assert response.status_code == 201

    page = client.get("/api/v1/finance/transfers?limit=1&offset=0", headers=owner_headers)
    assert page.status_code == 200
    assert len(page.json()) == 1
    assert page.json()[0]["amount"] == "10.25"

    all_transfers = client.get("/api/v1/finance/transfers", headers=owner_headers)
    assert all_transfers.status_code == 200
    assert len(all_transfers.json()) == 2
    assert client.get("/api/v1/finance/transfers", headers=other_headers).json() == []
