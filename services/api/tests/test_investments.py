import asyncio
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker,create_async_engine
from sfi_api.config import Settings
from sfi_api.database import get_session
from sfi_api.main import app
from sfi_api.models import Base

@pytest.fixture
def client(tmp_path,monkeypatch):
    engine=create_async_engine(f"sqlite+aiosqlite:///{tmp_path/'investments.db'}")
    factory=async_sessionmaker(engine,expire_on_commit=False)
    async def prepare():
        async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
    asyncio.run(prepare())
    async def override():
        async with factory() as session: yield session
    app.dependency_overrides[get_session]=override
    monkeypatch.setattr("sfi_api.security.get_settings",lambda:Settings(jwt_secret_key="test-only-secret-key-with-at-least-32-bytes"))
    with TestClient(app) as c: yield c
    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())

def register(c,email):
    r=c.post("/api/v1/auth/register",json={"email":email,"password":"senha-forte-teste-123"})
    assert r.status_code==201,r.text
    return {"Authorization":f"Bearer {r.json()['access_token']}"}

def test_portfolio_cost_basis_dividend_and_owner_isolation(client):
    h=register(client,"investor@example.com");other=register(client,"other@example.com")
    a=client.post("/api/v1/investments/assets",headers=h,json={"name":"ETF índice","ticker":"ETF11","asset_type":"etf"})
    assert a.status_code==201,a.text
    url=f"/api/v1/investments/assets/{a.json()['id']}/operations"
    def add(kind,amount,qty,price,key,fees="0.00"):
        return client.post(url,headers=h,json={"operation_type":kind,"amount":amount,"quantity":qty,"unit_price":price,"fees":fees,"occurred_at":"2026-11-16T12:00:00-03:00","idempotency_key":key})
    assert add("buy","1000.00","10","100","invest-buy-0000001","10.00").status_code==201
    assert add("buy","600.00","5","120","invest-buy-0000002").status_code==201
    assert add("sell","440.00","4","110","invest-sell-000001").status_code==201
    assert add("dividend","25.00","0","0","invest-dividend-0001").status_code==201
    p=client.get("/api/v1/investments/portfolio",headers=h)
    assert p.status_code==200,p.text
    row=p.json()[0]
    assert row["quantity"]=="11.00000000"
    assert row["invested_amount"]=="1180.67"
    assert row["dividends"]=="25.00"
    assert row["realized_result"]=="10.67"
    assert client.get("/api/v1/investments/assets",headers=other).json()==[]
    assert client.get(url,headers=other).status_code==404

def test_reject_oversell_and_idempotency_replay(client):
    h=register(client,"invest-sell@example.com")
    a=client.post("/api/v1/investments/assets",headers=h,json={"name":"Tesouro","asset_type":"bond"}).json()
    url=f"/api/v1/investments/assets/{a['id']}/operations"
    payload={"operation_type":"sell","amount":"10.00","quantity":"1","unit_price":"10","occurred_at":"2026-11-16T12:00:00Z","idempotency_key":"invest-sell-invalid-001"}
    assert client.post(url,headers=h,json=payload).status_code==422
    buy={**payload,"operation_type":"buy","idempotency_key":"invest-buy-valid-0001"}
    assert client.post(url,headers=h,json=buy).status_code==201
    assert client.post(url,headers=h,json=buy).status_code==409
