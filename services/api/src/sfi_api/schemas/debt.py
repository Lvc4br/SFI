import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DebtCreate(BaseModel):
    creditor: str = Field(min_length=1, max_length=120)
    debt_type: Literal["loan", "financing", "personal", "mortgage", "vehicle", "other"] = "other"
    description: str = Field(min_length=1, max_length=160)
    currency: str = Field(default="BRL", pattern=r"^[A-Z]{3}$")
    original_amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    outstanding_principal: Decimal | None = Field(
        default=None, ge=0, max_digits=18, decimal_places=2
    )
    annual_interest_rate: Decimal = Field(
        default=Decimal("0"), ge=0, max_digits=9, decimal_places=6
    )
    amortization_method: Literal["manual", "price", "sac"] = "manual"
    contracted_at: date
    first_due_date: date
    installment_count: int | None = Field(default=None, ge=1, le=600)
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("creditor", "description")
    @classmethod
    def trim_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Este campo não pode ficar vazio.")
        return value

    @field_validator("outstanding_principal")
    @classmethod
    def validate_principal(cls, value: Decimal | None, info):
        original = info.data.get("original_amount")
        if value is not None and original is not None and value > original:
            raise ValueError("O saldo devedor não pode superar o valor original.")
        return value


class DebtResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    creditor: str
    debt_type: str
    description: str
    currency: str
    original_amount: Decimal
    outstanding_principal: Decimal
    annual_interest_rate: Decimal
    amortization_method: str
    contracted_at: date
    first_due_date: date
    next_due_date: date | None
    installment_count: int | None
    status: Literal["active", "paid", "archived"]
    notes: str | None
    created_at: datetime


class DebtPaymentCreate(BaseModel):
    source_account_id: uuid.UUID
    principal_amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    interest_amount: Decimal = Field(
        default=Decimal("0"), ge=0, max_digits=18, decimal_places=2
    )
    paid_at: datetime
    next_due_date: date | None = None
    idempotency_key: str = Field(min_length=16, max_length=100)

    @field_validator("paid_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("A data do pagamento precisa conter fuso horário.")
        return value


class DebtPaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    debt_id: uuid.UUID
    source_account_id: uuid.UUID
    transaction_id: uuid.UUID
    amount: Decimal
    principal_amount: Decimal
    interest_amount: Decimal
    paid_at: datetime
    created_at: datetime



class DebtRefinancePreview(BaseModel):
    new_principal: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    monthly_effective_rate_percent: Decimal = Field(
        ge=0, max_digits=9, decimal_places=6
    )
    installment_count: int = Field(ge=1, le=600)
    amortization_method: Literal["price", "sac"]
    first_due_date: date
    financed_fees: Decimal = Field(
        default=Decimal("0"), ge=0, max_digits=18, decimal_places=2
    )
    monthly_fees: Decimal = Field(
        default=Decimal("0"), ge=0, max_digits=18, decimal_places=2
    )
