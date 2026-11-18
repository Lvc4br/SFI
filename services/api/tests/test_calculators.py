from fastapi.testclient import TestClient

from sfi_api.main import app


def test_compound_interest_zero_rate_and_monthly_contributions():
    with TestClient(app) as client:
        response = client.post("/api/v1/calculators/compound-interest", json={
            "principal": "1000.00", "monthly_contribution": "100.00",
            "annual_rate_percent": "0", "months": 12,
        })
    assert response.status_code == 200
    assert response.json()["future_value"] == "2200.00"
    assert response.json()["invested_amount"] == "2200.00"
    assert response.json()["interest_earned"] == "0.00"


def test_compound_interest_applies_monthly_compounding():
    with TestClient(app) as client:
        response = client.post("/api/v1/calculators/compound-interest", json={
            "principal": "1000.00", "monthly_contribution": "0",
            "annual_rate_percent": "12", "months": 12,
        })
    assert response.status_code == 200
    assert response.json()["future_value"] == "1126.83"
    assert response.json()["interest_earned"] == "126.83"


def test_loan_schedule_price_and_sac_balance_to_zero():
    with TestClient(app) as client:
        for method in ("price", "sac"):
            response = client.post("/api/v1/calculators/loan-schedule", json={
                "principal": "2500.00", "annual_rate_percent": "12",
                "installments": 3, "first_due_date": "2026-01-31", "method": method,
            })
            assert response.status_code == 200, response.text
            data = response.json()
            assert len(data["installments"]) == 3
            assert data["installments"][-1]["closing_balance"] == "0.00"
            assert data["principal_total"] == "2500.00"
            assert data["installments"][1]["due_date"] == "2026-02-28"
            assert data["is_estimate"] is True


def test_real_return_and_equivalent_rate():
    with TestClient(app) as client:
        real = client.post("/api/v1/calculators/real-return", json={
            "nominal_return_percent": "10", "inflation_percent": "5",
        })
        equivalent = client.post("/api/v1/calculators/equivalent-rate", json={
            "annual_nominal_rate_percent": "12", "compounds_per_year": 12,
        })
    assert real.status_code == 200
    assert real.json()["real_return_percent"] == "4.761905"
    assert equivalent.status_code == 200
    assert equivalent.json()["effective_annual_rate_percent"] == "12.682503"


def test_calculators_reject_invalid_ranges_and_unbounded_periods():
    with TestClient(app) as client:
        response = client.post("/api/v1/calculators/loan-schedule", json={
            "principal": "1000", "annual_rate_percent": "10",
            "installments": 601, "first_due_date": "2026-01-01", "method": "price",
        })
    assert response.status_code == 422



def test_cet_estimate_uses_actual_dated_cash_flows_and_upfront_costs():
    with TestClient(app) as client:
        response = client.post("/api/v1/calculators/cet-estimate", json={
            "gross_credit_amount": "10000.00",
            "upfront_costs": "500.00",
            "installment_amount": "950.00",
            "monthly_charges": "25.00",
            "installments": 12,
            "contract_date": "2026-01-01",
            "first_due_date": "2026-02-01",
        })
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["net_disbursement"] == "9500.00"
    assert data["upfront_costs"] == "500.00"
    assert data["total_paid"] == "11700.00"
    assert data["cash_flows"][0]["due_date"] == "2026-02-01"
    assert data["cash_flows"][-1]["due_date"] == "2027-01-01"
    assert Decimal(data["effective_annual_cost_percent"]) > 0
    assert data["is_estimate"] is True


def test_cet_estimate_rejects_non_positive_net_disbursement_and_past_due_date():
    with TestClient(app) as client:
        zero_net = client.post("/api/v1/calculators/cet-estimate", json={
            "gross_credit_amount": "1000.00", "upfront_costs": "1000.00",
            "installment_amount": "100.00", "installments": 12,
            "contract_date": "2026-01-01", "first_due_date": "2026-02-01",
        })
        past_due = client.post("/api/v1/calculators/cet-estimate", json={
            "gross_credit_amount": "1000.00", "installment_amount": "100.00",
            "installments": 12, "contract_date": "2026-02-01",
            "first_due_date": "2026-02-01",
        })
    assert zero_net.status_code == 422
    assert past_due.status_code == 422
