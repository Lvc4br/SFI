import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    brand: str | None = Field(default=None, max_length=100)
    category: str | None = Field(default=None, max_length=80)
    barcode: str | None = Field(default=None, min_length=8, max_length=32)
    unit: str = Field(default="un", min_length=1, max_length=20)

    @field_validator("name", "unit")
    @classmethod
    def trim_required(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("O campo não pode ficar vazio.")
        return value


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    brand: str | None
    category: str | None
    barcode: str | None
    unit: str
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PriceObservationCreate(BaseModel):
    price: Decimal = Field(ge=0, max_digits=18, decimal_places=2)
    currency: str = Field(default="BRL", min_length=3, max_length=3)
    merchant: str | None = Field(default=None, max_length=120)
    source: str = Field(default="manual", pattern="^(manual|receipt|import)$")
    notes: str | None = Field(default=None, max_length=300)
    observed_at: datetime

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        value = value.strip().upper()
        if len(value) != 3 or not value.isalpha():
            raise ValueError("A moeda deve ser um código ISO de três letras.")
        return value

    @field_validator("observed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("A data da observação precisa incluir fuso horário.")
        return value


class PriceObservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    product_id: uuid.UUID
    price: Decimal
    currency: str
    merchant: str | None
    source: str
    notes: str | None
    observed_at: datetime
    created_at: datetime
