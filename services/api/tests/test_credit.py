import asyncio
from datetime import date
from types import SimpleNamespace
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sfi_api.database import get_session
from sfi_api.main import app
from sfi_api.models import Base
from sfi_api.routers.credit import _cycle_dates

def register(client, email):
    response=client.post("/api/v1/auth/register",json={"email":email,"password":"senha-forte-teste-123"})
    assert response.status_code==201,response.text
    return response.json()["access_token"]

def test_installments_and_invoice_partial_payment(tmp_path):
    engine=create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'credit.db'}")
    factory=async_sessionmaker(engine,expire_on_commit=False)
    async def prepare():
        async with engine.begin() as connection: await connection.run_sync(Base.metadata.create_all)
    asyncio.run(prepare())
    async def override():
        async with factory() as session: yield session
    app.dependency_overrides[get_session]=override
    try:
        with TestClient(app) as client:
            headers={"Authorization":f"Bearer {register(client,'credit-test@example.com')}"}
            credit=client.post("/api/v1/finance/accounts",headers=headers,json={"name":"Cartão","account_type":"credit"})
            source=client.post("/api/v1/finance/accounts",headers=headers,json={"name":"Corrente","account_type":"checking"})
            card=client.post("/api/v1/credit/cards",headers=headers,json={"account_id":credit.json()["id"],"name":"Meu cartão","closing_day":10,"due_day":20,"credit_limit":"5000.00"})
            assert card.status_code==201,card.text
            purchase=client.post("/api/v1/credit/purchases",headers=headers,json={"card_id":card.json()["id"],"description":"Notebook","amount":"1000.00","purchase_date":"2026-11-12","installments":3,"idempotency_key":"purchase-notebook-2026-001"})
            assert purchase.status_code==201,purchase.text
            invoices=client.get("/api/v1/credit/invoices",headers=headers).json()
            assert len(invoices)==3
            assert {row["period"] for row in invoices}=={"2026-12","2027-01","2027-02"}
            first=next(row for row in invoices if row["period"]=="2026-12")
            payment=client.post(f"/api/v1/credit/invoices/{first['id']}/payments",headers=headers,json={"source_account_id":source.json()["id"],"amount":"100.00","paid_at":"2026-11-15T12:00:00Z","idempotency_key":"payment-notebook-001"})
            assert payment.status_code==201,payment.text
            again=client.post(f"/api/v1/credit/invoices/{first['id']}/payments",headers=headers,json={"source_account_id":source.json()["id"],"amount":"100.00","paid_at":"2026-11-15T12:00:00Z","idempotency_key":"payment-notebook-001"})
            assert again.status_code==409
            updated=client.get("/api/v1/credit/invoices",headers=headers).json()
            row=next(item for item in updated if item["id"]==first["id"])
            assert row["paid_amount"]=="100.00"
            assert row["remaining_amount"]=="233.33"
    finally:
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())

def test_cycle_handles_short_month_and_due_month():
    period,closing,due=_cycle_dates(SimpleNamespace(closing_day=31,due_day=10),date(2027,1,31))
    assert period=="2027-02"
    assert closing==date(2027,2,28)
    assert due==date(2027,3,10)
