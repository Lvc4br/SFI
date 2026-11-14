import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    account_type: Literal["checking", "savings", "cash", "credit"]
    currency: str = Field(default="BRL", pattern=r"^[A-Z]{3}$")
    opening_balance: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=18, decimal_places=2)


class AccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    account_type: str
    currency: str
    opening_balance: Decimal
    created_at: datetime


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    category_type: Literal["income", "expense"]

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("O nome da categoria não pode ficar vazio.")
        return value


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    category_type: str
    created_at: datetime


class TransactionCreate(BaseModel):
    account_id: uuid.UUID
    category_id: uuid.UUID | None = None
    transaction_type: Literal["income", "expense"]
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    description: str = Field(min_length=1, max_length=160)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    idempotency_key: str = Field(min_length=16, max_length=100)

    @field_validator("description")
    @classmethod
    def trim_description(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("A descrição não pode ficar vazia.")
        return value

    @field_validator("occurred_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("A data da movimentação precisa conter fuso horário.")
        return value


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    account_id: uuid.UUID
    category_id: uuid.UUID | None
    transaction_type: str
    amount: Decimal
    currency: str
    description: str
    occurred_at: datetime
    created_at: datetime


class AccountBalanceResponse(BaseModel):
    account_id: uuid.UUID
    name: str
    account_type: str
    currency: str
    opening_balance: Decimal
    income_total: Decimal
    expense_total: Decimal
    balance: Decimal
    balance_kind: Literal["available_balance", "credit_used"]


class CurrencyTotals(BaseModel):
    currency: str
    income_total: Decimal
    expense_total: Decimal
    net_flow: Decimal


class CategorySpending(BaseModel):
    category_id: uuid.UUID
    category_name: str
    currency: str
    amount: Decimal


class FinanceSummaryResponse(BaseModel):
    start_date: date
    end_date: date
    totals_by_currency: list[CurrencyTotals]
    account_balances: list[AccountBalanceResponse]
    spending_by_category: list[CategorySpending]


class BudgetCreate(BaseModel):
    category_id: uuid.UUID
    period: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    currency: str = Field(default="BRL", pattern=r"^[A-Z]{3}$")
    limit_amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)


class BudgetResponse(BaseModel):
    id: uuid.UUID
    category_id: uuid.UUID
    category_name: str
    period: str
    currency: str
    limit_amount: Decimal
    spent_amount: Decimal
    remaining_amount: Decimal
    usage_percent: Decimal
    status: Literal["within_limit", "reached_limit", "over_limit"]
    created_at: datetime
