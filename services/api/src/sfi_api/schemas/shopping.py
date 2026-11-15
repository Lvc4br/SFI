import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ShoppingListCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    is_favorite: bool = False

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("O nome da lista não pode ficar vazio.")
        return value


class ShoppingListUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    is_favorite: bool | None = None


class ShoppingListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    is_favorite: bool
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ShoppingItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    quantity: Decimal = Field(default=Decimal("1.000"), gt=0, max_digits=12, decimal_places=3)
    unit: str = Field(default="un", min_length=1, max_length=20)
    unit_price: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    notes: str | None = Field(default=None, max_length=300)
    position: int = Field(default=0, ge=0)

    @field_validator("name", "unit")
    @classmethod
    def trim_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("O campo não pode ficar vazio.")
        return value


class ShoppingItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    quantity: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=3)
    unit: str | None = Field(default=None, min_length=1, max_length=20)
    unit_price: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    is_checked: bool | None = None
    notes: str | None = Field(default=None, max_length=300)
    position: int | None = Field(default=None, ge=0)


class ShoppingItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    list_id: uuid.UUID
    name: str
    quantity: Decimal
    unit: str
    unit_price: Decimal | None
    is_checked: bool
    position: int
    notes: str | None
    created_at: datetime


class ShoppingListDetail(ShoppingListResponse):
    items: list[ShoppingItemResponse]
