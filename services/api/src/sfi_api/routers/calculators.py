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
    monthly_contribution: Decimal = Field(
        default=Decimal("0"), ge=0, max_digits=18, decimal_places=2
    )
    annual_rate_percent: Decimal = Field(
        ge=Decimal("-99.999999"), le=1000, max_digits=10, decimal_places=6
    )
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
    nominal_return_percent: Decimal = Field(
        gt=Decimal("-100"), le=10000, max_digits=12, decimal_places=6
    )
    inflation_percent: Decimal = Field(
        gt=Decimal("-100"), le=10000, max_digits=12, decimal_places=6
    )


class EquivalentRateInput(BaseModel):
    annual_nominal_rate_percent: Decimal = Field(
        gt=Decimal("-100"), le=10000, max_digits=12, decimal_places=6
    )
    compounds_per_year: int = Field(ge=1, le=365)


class LatePaymentInput(BaseModel):
    principal: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    due_date: date
    payment_date: date
    penalty_percent: Decimal = Field(default=Decimal("2"), ge=0, le=100, max_digits=8, decimal_places=4)
    monthly_interest_percent: Decimal = Field(default=Decimal("1"), ge=0, le=100, max_digits=8, decimal_places=4)
    interest_method: Literal["simple", "compound"] = "simple"
    index_correction_factor: Decimal = Field(default=Decimal("1"), ge=Decimal("0.1"), le=10, max_digits=10, decimal_places=6)

    @field_validator("principal", "penalty_percent", "monthly_interest_percent", "index_correction_factor")
    @classmethod
    def reject_non_finite_late_payment_values(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("Informe um número finito.")
        return value


class CetEstimateInput(BaseModel):
    gross_credit_amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    upfront_costs: Decimal = Field(default=Decimal("0"), ge=0, max_digits=18, decimal_places=2)
    installment_amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    monthly_charges: Decimal = Field(default=Decimal("0"), ge=0, max_digits=18, decimal_places=2)
    installments: int = Field(ge=1, le=600)
    contract_date: date
    first_due_date: date

    @field_validator("gross_credit_amount", "upfront_costs", "installment_amount", "monthly_charges")
    @classmethod
    def reject_non_finite_cet_values(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("Informe um número finito.")
        return value


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
        "periodic_rate_percent": str(
            (periodic * HUNDRED).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
        ),
        "effective_annual_rate_percent": str(
            effective.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
        ),
        "compounds_per_year": payload.compounds_per_year,
        "is_estimate": True,
    }



@router.post("/cet-estimate")
def cet_estimate(payload: CetEstimateInput) -> dict:
    """Estimate the effective annual cost from borrower cash flows (not an official CET statement)."""
    net_disbursement = money(payload.gross_credit_amount - payload.upfront_costs)
    if net_disbursement <= 0:
        from fastapi import HTTPException

        raise HTTPException(422, "Os custos iniciais devem ser menores que o crédito bruto.")

    payments = []
    for index in range(payload.installments):
        due_date = add_months(payload.first_due_date, index)
        payment = money(payload.installment_amount + payload.monthly_charges)
        payments.append({"number": index + 1, "due_date": due_date, "payment": payment})

    total_paid = money(sum((row["payment"] for row in payments), Decimal("0")))
    day_offsets = [(row["due_date"] - payload.contract_date).days for row in payments]
    if any(days <= 0 for days in day_offsets):
        from fastapi import HTTPException

        raise HTTPException(422, "O primeiro vencimento deve ocorrer após a liberação do crédito.")

    def present_value(annual_rate: Decimal) -> Decimal:
        base = Decimal("1") + annual_rate
        return sum(
            (
                row["payment"] / (base ** (Decimal(days) / Decimal("365")))
                for row, days in zip(payments, day_offsets, strict=True)
            ),
            Decimal("0"),
        ) - net_disbursement

    with localcontext() as context:
        context.prec = 50
        low = Decimal("-0.999999")
        high = Decimal("1000000")
        low_value = present_value(low)
        high_value = present_value(high)
        if low_value <= 0 or high_value >= 0:
            from fastapi import HTTPException

            raise HTTPException(422, "Não foi possível encontrar uma taxa efetiva para os fluxos informados.")
        for _ in range(220):
            middle = (low + high) / Decimal("2")
            if present_value(middle) > 0:
                low = middle
            else:
                high = middle
        annual_rate = (low + high) / Decimal("2")
        monthly_rate = (Decimal("1") + annual_rate) ** (Decimal("1") / Decimal("12")) - 1

    return {
        "currency": "BRL",
        "net_disbursement": str(net_disbursement),
        "total_paid": str(total_paid),
        "upfront_costs": str(money(payload.upfront_costs)),
        "monthly_charges_total": str(money(payload.monthly_charges * payload.installments)),
        "effective_annual_cost_percent": str((annual_rate * HUNDRED).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)),
        "effective_monthly_cost_percent": str((monthly_rate * HUNDRED).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)),
        "cash_flows": [
            {"number": row["number"], "due_date": row["due_date"].isoformat(), "payment": str(row["payment"])}
            for row in payments
        ],
        "is_estimate": True,
        "assumptions": [
            "Taxa efetiva anual estimada por valor presente dos fluxos e dias reais/365.",
            "O valor líquido liberado é o crédito bruto menos os custos iniciais informados.",
            "Cada parcela inclui o encargo mensal informado; custos variáveis devem ser incluídos no valor de cada parcela.",
            "Não substitui o CET oficial da instituição financeira nem valida tarifas, tributos ou contrato.",
        ],
    }



@router.post("/late-payment-estimate")
def late_payment_estimate(payload: LatePaymentInput) -> dict:
    days_overdue = max(0, (payload.payment_date - payload.due_date).days)
    with localcontext() as context:
        context.prec = 40
        corrected_principal = money(payload.principal * payload.index_correction_factor)
        penalty = money(corrected_principal * payload.penalty_percent / HUNDRED) if days_overdue else Decimal("0.00")
        monthly_rate = payload.monthly_interest_percent / HUNDRED
        if not days_overdue or monthly_rate == 0:
            interest = Decimal("0.00")
        elif payload.interest_method == "simple":
            interest = money(corrected_principal * monthly_rate * Decimal(days_overdue) / Decimal("30"))
        else:
            period_factor = (Decimal("1") + monthly_rate) ** (Decimal(days_overdue) / Decimal("30"))
            interest = money(corrected_principal * (period_factor - Decimal("1")))
        total = money(corrected_principal + penalty + interest)
    return {
        "currency": "BRL",
        "principal": str(money(payload.principal)),
        "corrected_principal": str(corrected_principal),
        "days_overdue": days_overdue,
        "penalty": str(penalty),
        "interest": str(interest),
        "total_due": str(total),
        "interest_method": payload.interest_method,
        "index_correction_factor": str(payload.index_correction_factor),
        "is_estimate": True,
        "assumptions": [
            "A multa é aplicada uma única vez sobre o principal corrigido e somente quando há atraso.",
            "Juros simples ou compostos são calculados proporcionalmente a períodos de 30 dias.",
            "O fator de correção é informado manualmente; o SFI não consulta índices econômicos.",
            "Use apenas percentuais e critérios previstos no contrato e na legislação aplicável.",
        ],
    }
