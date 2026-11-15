import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

class CreditCardCreate(BaseModel):
    account_id: uuid.UUID
    name: str = Field(min_length=1, max_length=80)
    brand: str | None = Field(default=None, max_length=30)
    last_four: str | None = Field(default=None, pattern=r"^\d{4}$")
    closing_day: int = Field(ge=1, le=31)
    due_day: int = Field(ge=1, le=31)
    credit_limit: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value=value.strip()
        if not value: raise ValueError("Informe um nome para o cartão.")
        return value

class CreditCardResponse(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    id: uuid.UUID
    account_id: uuid.UUID
    name: str
    brand: str | None
    last_four: str | None
    closing_day: int
    due_day: int
    credit_limit: Decimal
    created_at: datetime

class CreditPurchaseCreate(BaseModel):
    card_id: uuid.UUID
    description: str = Field(min_length=1, max_length=160)
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    purchase_date: date
    installments: int = Field(default=1, ge=1, le=48)
    idempotency_key: str = Field(min_length=16, max_length=100)
    @field_validator("description")
    @classmethod
    def clean_description(cls, value: str) -> str:
        value=value.strip()
        if not value: raise ValueError("Informe a descrição da compra.")
        return value

class CreditInvoiceResponse(BaseModel):
    id: uuid.UUID
    card_id: uuid.UUID
    period: str
    closing_date: date
    due_date: date
    status: Literal["open", "closed", "paid"]
    total_amount: Decimal
    paid_amount: Decimal
    remaining_amount: Decimal

class CreditInvoicePaymentCreate(BaseModel):
    source_account_id: uuid.UUID
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    paid_at: datetime
    idempotency_key: str = Field(min_length=16, max_length=100)
    @field_validator("paid_at")
    @classmethod
    def aware_date(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("A data do pagamento precisa conter fuso horário.")
        return value

class CreditInvoicePaymentResponse(BaseModel):
    id: uuid.UUID
    invoice_id: uuid.UUID
    amount: Decimal
    paid_at: datetime
    created_at: datetime
