"""Validator tests: the deterministic guards that keep absurd inputs out of the pipeline."""
from app.functions.validator import validate_inputs


def _customer(salary=22000):
    return {"customer_id": "C1", "salary": salary}


def _accounts():
    return [{"customer_id": "C1", "bank_code": "ALRAJHI", "balance": 5000}]


def _transactions(n=6):
    return [
        {"customer_id": "C1", "transaction_date": f"2026-{m:02d}-05", "raw_description": "POS X",
         "transaction_type": "expense", "amount": -100}
        for m in range(1, n + 1)
    ]


def test_installment_at_or_above_salary_is_blocked():
    result = validate_inputs(
        _customer(salary=22000), _accounts(), _transactions(), [],
        {"monthly_installment": 22000},
    )
    assert result["is_valid"] is False
    assert result["blocking_errors_ar"]


def test_absurd_installment_from_the_report_is_blocked():
    # 1,000,000 loan / 20,000 installment vs a 22,000 salary -> would be nonsense to analyze.
    result = validate_inputs(
        _customer(salary=22000), _accounts(), _transactions(), [],
        {"monthly_installment": 25000},
    )
    assert result["is_valid"] is False


def test_high_but_analyzable_installment_only_warns():
    result = validate_inputs(
        _customer(salary=22000), _accounts(), _transactions(), [],
        {"monthly_installment": 15000},
    )
    assert result["is_valid"] is True
    assert result["warnings_ar"]


def test_customer_id_mismatch_blocks():
    accounts = [{"customer_id": "OTHER", "bank_code": "SNB", "balance": 1}]
    result = validate_inputs(_customer(), accounts, _transactions(), [], None)
    assert result["is_valid"] is False
