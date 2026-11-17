import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GoalCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    currency: str = Field(default="BRL", pattern=r"^[A-Z]{3}$")
    target_amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    target_date: date | None = None

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Informe o nome da meta.")
        return value


class GoalUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    target_amount: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=2)
    target_date: date | None = None
    status: Literal["active", "paused", "archived"] | None = None

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Informe o nome da meta.")
        return value


class GoalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    currency: str
    target_amount: Decimal
    current_amount: Decimal
    target_date: date | None
    status: Literal["active", "completed", "paused", "archived"]
    created_at: datetime
    updated_at: datetime


class GoalEntryCreate(BaseModel):
    entry_type: Literal["contribution", "withdrawal"]
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    description: str | None = Field(default=None, max_length=200)
    occurred_at: datetime
    idempotency_key: str = Field(min_length=16, max_length=100)

    @field_validator("occurred_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("A data do movimento precisa conter fuso horário.")
        return value


class GoalEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    goal_id: uuid.UUID
    entry_type: Literal["contribution", "withdrawal"]
    amount: Decimal
    description: str | None
    occurred_at: datetime
    created_at: datetime
