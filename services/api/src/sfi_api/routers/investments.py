import uuid
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sfi_api.database import get_session
from sfi_api.dependencies import get_current_user
from sfi_api.models.investments import InvestmentAsset, InvestmentOperation
from sfi_api.models.user import User

router=APIRouter(prefix="/investments",tags=["investments"])
SESSION=Depends(get_session)
USER=Depends(get_current_user)
AssetType=Literal["stock","reit","etf","bond","fund","crypto","fixed_income","other"]
OperationType=Literal["buy","sell","dividend","fee","tax"]

class AssetIn(BaseModel):
    name:str=Field(min_length=1,max_length=120)
    ticker:str|None=Field(default=None,max_length=24)
    asset_type:AssetType
    currency:str=Field(default="BRL",pattern=r"^[A-Z]{3}$")
    notes:str|None=Field(default=None,max_length=500)
    @field_validator("name")
    @classmethod
    def clean_name(cls,v):
        if not v.strip(): raise ValueError("Informe o nome do ativo.")
        return v.strip()

class AssetOut(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    id:uuid.UUID
    name:str
    ticker:str|None
    asset_type:AssetType
    currency:str
    notes:str|None
    archived:bool
    created_at:datetime

class OperationIn(BaseModel):
    operation_type:OperationType
    amount:Decimal=Field(ge=0,max_digits=18,decimal_places=2)
    quantity:Decimal=Field(default=Decimal("0"),ge=0,max_digits=24,decimal_places=8)
    unit_price:Decimal=Field(default=Decimal("0"),ge=0,max_digits=18,decimal_places=8)
    fees:Decimal=Field(default=Decimal("0"),ge=0,max_digits=18,decimal_places=2)
    taxes:Decimal=Field(default=Decimal("0"),ge=0,max_digits=18,decimal_places=2)
    notes:str|None=Field(default=None,max_length=500)
    idempotency_key:str=Field(min_length=16,max_length=100)
    occurred_at:datetime
    @field_validator("occurred_at")
    @classmethod
    def timezone_required(cls,v):
        if v.tzinfo is None or v.utcoffset() is None: raise ValueError("A data precisa conter fuso horário.")
        return v
    @model_validator(mode="after")
    def valid_amount(self):
        if self.operation_type in {"buy","sell"}:
            if self.quantity<=0 or self.unit_price<=0: raise ValueError("Compra/venda exigem quantidade e preço positivos.")
            if self.amount!=(self.quantity*self.unit_price).quantize(Decimal("0.01")): raise ValueError("Valor total incompatível com quantidade e preço.")
        elif self.amount<=0: raise ValueError("Informe valor positivo.")
        return self

class OperationOut(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    id:uuid.UUID
    asset_id:uuid.UUID
    operation_type:OperationType
    amount:Decimal
    quantity:Decimal
    unit_price:Decimal
    fees:Decimal
    taxes:Decimal
    notes:str|None
    occurred_at:datetime
    created_at:datetime

class Position(BaseModel):
    asset:AssetOut
    quantity:Decimal
    average_cost:Decimal
    invested_amount:Decimal
    dividends:Decimal
    realized_result:Decimal
    operations_count:int

@router.post("/assets",response_model=AssetOut,status_code=201)
async def create_asset(payload:AssetIn,session:AsyncSession=SESSION,user:User=USER):
    row=InvestmentAsset(user_id=user.id,**payload.model_dump());session.add(row);await session.commit();await session.refresh(row);return row

@router.get("/assets",response_model=list[AssetOut])
async def list_assets(include_archived:bool=False,session:AsyncSession=SESSION,user:User=USER):
    q=select(InvestmentAsset).where(InvestmentAsset.user_id==user.id)
    if not include_archived:q=q.where(InvestmentAsset.archived.is_(False))
    return list((await session.scalars(q.order_by(InvestmentAsset.name))).all())

@router.get("/assets/{asset_id}/operations",response_model=list[OperationOut])
async def list_operations(asset_id:uuid.UUID,session:AsyncSession=SESSION,user:User=USER):
    exists=await session.scalar(select(InvestmentAsset.id).where(InvestmentAsset.id==asset_id,InvestmentAsset.user_id==user.id))
    if not exists:raise HTTPException(404,"Ativo não encontrado.")
    rows=await session.scalars(select(InvestmentOperation).where(InvestmentOperation.asset_id==asset_id,InvestmentOperation.user_id==user.id).order_by(InvestmentOperation.occurred_at.desc()))
    return list(rows.all())

@router.post("/assets/{asset_id}/operations",response_model=OperationOut,status_code=201)
async def create_operation(asset_id:uuid.UUID,payload:OperationIn,session:AsyncSession=SESSION,user:User=USER):
    asset=await session.scalar(select(InvestmentAsset).where(InvestmentAsset.id==asset_id,InvestmentAsset.user_id==user.id,InvestmentAsset.archived.is_(False)).with_for_update())
    if not asset:raise HTTPException(404,"Ativo não encontrado ou arquivado.")
    duplicate=await session.scalar(select(InvestmentOperation.id).where(InvestmentOperation.user_id==user.id,InvestmentOperation.idempotency_key==payload.idempotency_key))
    if duplicate:raise HTTPException(409,"Chave de idempotência já utilizada.")
    if payload.operation_type=="sell":
        ops=await session.scalars(select(InvestmentOperation).where(InvestmentOperation.asset_id==asset_id,InvestmentOperation.user_id==user.id).order_by(InvestmentOperation.occurred_at,InvestmentOperation.created_at))
        held=sum((o.quantity if o.operation_type=="buy" else -o.quantity if o.operation_type=="sell" else Decimal("0")) for o in ops)
        if payload.quantity>held:raise HTTPException(422,"A venda supera a quantidade disponível.")
    row=InvestmentOperation(user_id=user.id,asset_id=asset_id,**payload.model_dump());session.add(row)
    try:await session.commit();await session.refresh(row)
    except IntegrityError:await session.rollback();raise HTTPException(409,"Operação duplicada ou conflitante.") from None
    return row

@router.get("/portfolio",response_model=list[Position])
async def portfolio(session:AsyncSession=SESSION,user:User=USER):
    assets=await session.scalars(select(InvestmentAsset).where(InvestmentAsset.user_id==user.id,InvestmentAsset.archived.is_(False)).order_by(InvestmentAsset.name))
    output=[]
    for asset in assets.all():
        ops=await session.scalars(select(InvestmentOperation).where(InvestmentOperation.asset_id==asset.id,InvestmentOperation.user_id==user.id).order_by(InvestmentOperation.occurred_at,InvestmentOperation.created_at))
        qty,cost,dividends,realized=Decimal("0"),Decimal("0"),Decimal("0"),Decimal("0")
        rows=list(ops.all())
        for op in rows:
            if op.operation_type=="buy":qty+=op.quantity;cost+=op.amount+op.fees+op.taxes
            elif op.operation_type=="sell":
                removed=(cost/qty)*op.quantity if qty else Decimal("0")
                realized+=op.amount-op.fees-op.taxes-removed;qty-=op.quantity;cost-=removed
            elif op.operation_type=="dividend":dividends+=op.amount
        avg=(cost/qty).quantize(Decimal("0.00000001"),rounding=ROUND_HALF_UP) if qty else Decimal("0")
        output.append(Position(asset=asset,quantity=qty,average_cost=avg,invested_amount=cost.quantize(Decimal("0.01")),dividends=dividends.quantize(Decimal("0.01")),realized_result=realized.quantize(Decimal("0.01")),operations_count=len(rows)))
    return output
