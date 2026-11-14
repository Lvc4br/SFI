from datetime import date, datetime
from decimal import Decimal
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RecurrenceCreate(BaseModel):
    account_id: uuid.UUID
    category_id: uuid.UUID | None = None
    transaction_type: Literal["income", "expense"]
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    description: str = Field(min_length=1, max_length=160)
    idempotency_key: str = Field(min_length=16, max_length=100)
    frequency: Literal["weekly", "monthly", "yearly"]
    interval_count: int = Field(default=1, ge=1, le=52)
    start_date: date
    end_date: date | None = None

    @field_validator("description")
    @classmethod
    def trim_description(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("A descrição não pode ficar vazia.")
        return value

    @model_validator(mode="after")
    def validate_date_range(self):
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("A data final não pode ser anterior à data inicial.")
        return self


class RecurrenceStatusUpdate(BaseModel):
    is_active: bool


class RecurrenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_id: uuid.UUID
    category_id: uuid.UUID | None
    transaction_type: str
    amount: Decimal
    currency: str
    description: str
    frequency: str
    interval_count: int
    start_date: date
    end_date: date | None
    is_active: bool
    created_at: datetime


class ForecastOccurrence(BaseModel):
    recurrence_id: uuid.UUID
    account_id: uuid.UUID
    account_name: str
    category_id: uuid.UUID | None
    transaction_type: Literal["income", "expense"]
    amount: Decimal
    currency: str
    description: str
    due_date: date


class ForecastCurrencyTotal(BaseModel):
    currency: str
    income_total: Decimal
    expense_total: Decimal
    net_flow: Decimal


class CashFlowForecastResponse(BaseModel):
    start_date: date
    end_date: date
    occurrences: list[ForecastOccurrence]
    totals_by_currency: list[ForecastCurrencyTotal]
