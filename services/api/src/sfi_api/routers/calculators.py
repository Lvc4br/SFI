import calendar
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, localcontext
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field, field_validator

router = APIRouter(prefix="/calculators", tags=["calculators"])
CENT = Decimal("0.01")
HUNDRED = Decimal("100")


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def add_months(value: date, months: int) -> date:
    index = value.month - 1 + months
    year = value.year + index // 12
    month = index % 12 + 1
    return date(year, month, min(value.day, calendar.monthrange(year, month)[1]))


class CompoundInterestInput(BaseModel):
    principal: Decimal = Field(ge=0, max_digits=18, decimal_places=2)
    monthly_contribution: Decimal = Field(default=Decimal("0"), ge=0, max_digits=18, decimal_places=2)
    annual_rate_percent: Decimal = Field(ge=Decimal("-99.999999"), le=1000, max_digits=10, decimal_places=6)
    months: int = Field(ge=1, le=1200)

    @field_validator("principal", "monthly_contribution", "annual_rate_percent")
    @classmethod
    def reject_non_finite(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("Informe um número finito.")
        return value


class LoanCalculatorInput(BaseModel):
    principal: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    annual_rate_percent: Decimal = Field(ge=0, le=1000, max_digits=10, decimal_places=6)
    installments: int = Field(ge=1, le=600)
    first_due_date: date
    method: Literal["price", "sac"]

    @field_validator("principal", "annual_rate_percent")
    @classmethod
    def reject_non_finite(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("Informe um número finito.")
        return value


class RealReturnInput(BaseModel):
    nominal_return_percent: Decimal = Field(gt=Decimal("-100"), le=10000, max_digits=12, decimal_places=6)
    inflation_percent: Decimal = Field(gt=Decimal("-100"), le=10000, max_digits=12, decimal_places=6)


class EquivalentRateInput(BaseModel):
    annual_nominal_rate_percent: Decimal = Field(gt=Decimal("-100"), le=10000, max_digits=12, decimal_places=6)
    compounds_per_year: int = Field(ge=1, le=365)


@router.post("/compound-interest")
def compound_interest(payload: CompoundInterestInput) -> dict:
    monthly_rate = payload.annual_rate_percent / HUNDRED / Decimal("12")
    with localcontext() as context:
        context.prec = 40
        factor = (Decimal("1") + monthly_rate) ** payload.months
        if monthly_rate == 0:
            future_principal = payload.principal
            contributions = payload.monthly_contribution * payload.months
        else:
            future_principal = payload.principal * factor
            contributions = payload.monthly_contribution * ((factor - 1) / monthly_rate)
        total = money(future_principal + contributions)
        invested = money(payload.principal + payload.monthly_contribution * payload.months)
        return {
            "currency": "BRL",
            "future_value": str(total),
            "invested_amount": str(invested),
            "interest_earned": str(money(total - invested)),
            "monthly_rate_percent": str(monthly_rate * HUNDRED),
            "months": payload.months,
            "assumptions": [
                "Taxa anual nominal convertida em taxa mensal por divisão por 12.",
                "Aportes mensais ocorrem ao final de cada mês.",
                "Valores são projeções matemáticas, sem impostos, tarifas ou variação de taxa.",
            ],
        }


@router.post("/loan-schedule")
def loan_schedule(payload: LoanCalculatorInput) -> dict:
    monthly_rate = payload.annual_rate_percent / HUNDRED / Decimal("12")
    principal = money(payload.principal)
    count = payload.installments
    with localcontext() as context:
        context.prec = 40
        if payload.method == "price":
            if monthly_rate == 0:
                fixed_payment = money(principal / Decimal(count))
            else:
                factor = (Decimal("1") + monthly_rate) ** count
                fixed_payment = money(principal * monthly_rate * factor / (factor - 1))
        else:
            fixed_payment = None

        balance = principal
        rows = []
        for number in range(1, count + 1):
            opening = balance
            interest = money(opening * monthly_rate)
            if payload.method == "sac":
                amortization = balance if number == count else money(principal / Decimal(count))
            else:
                amortization = balance if number == count else min(
                    balance, max(Decimal("0.00"), money(fixed_payment - interest))
                )
            payment = money(amortization + interest)
            balance = money(max(Decimal("0.00"), balance - amortization))
            rows.append({
                "number": number,
                "due_date": add_months(payload.first_due_date, number - 1).isoformat(),
                "opening_balance": str(opening),
                "amortization": str(money(amortization)),
                "interest": str(interest),
                "payment": str(payment),
                "closing_balance": str(balance),
            })

        principal_total = money(sum((Decimal(row["amortization"]) for row in rows), Decimal("0")))
        interest_total = money(sum((Decimal(row["interest"]) for row in rows), Decimal("0")))
        payment_total = money(sum((Decimal(row["payment"]) for row in rows), Decimal("0")))

    return {
        "method": payload.method,
        "currency": "BRL",
        "monthly_rate_percent": str(monthly_rate * HUNDRED),
        "installments": rows,
        "principal_total": str(principal_total),
        "interest_total": str(interest_total),
        "payment_total": str(payment_total),
        "is_estimate": True,
        "assumptions": [
            "Taxa anual nominal dividida por 12; não representa CET.",
            "Sem seguros, tarifas, impostos, multas, mora ou indexadores.",
            "A última amortização é ajustada para zerar o saldo por arredondamento.",
            "Datas mensais preservam o dia inicial e ajustam meses curtos para o último dia.",
        ],
    }


@router.post("/real-return")
def real_return(payload: RealReturnInput) -> dict:
    nominal = payload.nominal_return_percent / HUNDRED
    inflation = payload.inflation_percent / HUNDRED
    with localcontext() as context:
        context.prec = 40
        result = ((Decimal("1") + nominal) / (Decimal("1") + inflation) - 1) * HUNDRED
    return {
        "real_return_percent": str(result.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)),
        "formula": "((1 + retorno nominal) / (1 + inflação) - 1) × 100",
        "is_estimate": True,
    }


@router.post("/equivalent-rate")
def equivalent_rate(payload: EquivalentRateInput) -> dict:
    annual_nominal = payload.annual_nominal_rate_percent / HUNDRED
    periodic = annual_nominal / Decimal(payload.compounds_per_year)
    with localcontext() as context:
        context.prec = 40
        effective = ((Decimal("1") + periodic) ** payload.compounds_per_year - 1) * HUNDRED
    return {
        "periodic_rate_percent": str((periodic * HUNDRED).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)),
        "effective_annual_rate_percent": str(effective.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)),
        "compounds_per_year": payload.compounds_per_year,
        "is_estimate": True,
    }
