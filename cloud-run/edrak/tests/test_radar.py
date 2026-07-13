"""Radar tests: gap detection is arithmetic over the trajectory, not vibes."""
from datetime import date

from app.functions.radar import run_radar


TODAY = date(2026, 7, 10)


def _txn(day_iso, amount, category, txn_type="expense"):
    return {
        "transaction_id": f"T-{day_iso}-{amount}",
        "customer_id": "CUST999",
        "transaction_date": day_iso,
        "amount": amount,
        "category": category,
        "transaction_type": txn_type,
        "raw_description": "POS TEST",
    }


def _fixture(balance):
    profile = {"customer_id": "CUST999", "salary": 14500, "salary_day": 1}
    accounts = [{"account_id": "A1", "customer_id": "CUST999", "bank_code": "ALRAJHI", "balance": balance}]
    loans = [{"loan_id": "L1", "customer_id": "CUST999", "bank_code": "RIYAD", "loan_type": "car",
              "status": "active", "monthly_installment": 3100, "remaining_months": 22,
              "first_installment_date": "2025-05-27"}]
    obligations = [{"obligation_type": "bnpl_installment", "counterparty": "Tabby",
                    "monthly_amount": 220, "day_of_month": 21, "remaining_months": 3,
                    "confidence": 0.9, "is_committed": True}]
    transactions = [_txn("2026-07-01", 14500, "salary", "income")]
    # Three prior months: steady cafes (80 SAR x4) and groceries (150 SAR x2).
    for month in ("2026-04", "2026-05", "2026-06"):
        for day, amount in ((4, -80), (9, -80), (18, -80), (25, -80)):
            transactions.append(_txn(f"{month}-{day:02d}", amount, "cafes"))
        for day in (5, 15):
            transactions.append(_txn(f"{month}-{day:02d}", -150, "groceries"))
    # Current month: cafes more than doubled by day 10; groceries on pace.
    transactions += [
        _txn("2026-07-03", -200, "cafes"),
        _txn("2026-07-08", -200, "cafes"),
        _txn("2026-07-09", -300, "cafes"),
        _txn("2026-07-06", -150, "groceries"),
    ]
    return profile, accounts, transactions, loans, obligations


def test_gap_detected_before_the_loan_installment():
    result = run_radar(*_fixture(balance=4200), today=TODAY)
    assert result["has_gap"] is True
    # Pace: 850 spent / 10 days = 85/day. Available on day 27:
    # 4200 - 220 (Tabby day 21) - 85 * 17 days = 2535 → gap = 3100 - 2535.
    assert result["gap_amount"] == 565
    assert result["gap_date"] == "2026-07-27"
    assert result["cause_category"]["category"] == "cafes"
    assert result["cause_category"]["deviation_pct"] > 200


def test_no_gap_when_the_balance_is_healthy():
    result = run_radar(*_fixture(balance=10000), today=TODAY)
    assert result["has_gap"] is False
    assert result["gap_amount"] is None
    # The trajectory still carries the proof numbers for the "belt secure" state.
    assert result["trajectory"]["balance_now"] == 10000
    assert result["trajectory"]["upcoming_payments"][0]["day"] == 21


def test_categories_report_month_to_date_deviation():
    result = run_radar(*_fixture(balance=4200), today=TODAY)
    rows = {row["category"]: row for row in result["trajectory"]["categories"]}
    assert rows["cafes"]["mtd"] == 700
    assert rows["cafes"]["baseline_mtd"] == 160
    assert rows["groceries"]["deviation_pct"] == 0


def test_savings_are_a_reserve_not_spendable():
    profile, accounts, transactions, loans, obligations = _fixture(balance=4200)
    accounts.append({"account_id": "A2", "customer_id": "CUST999", "bank_code": "ALINMA",
                     "account_type": "savings", "balance": 50000})
    result = run_radar(profile, accounts, transactions, loans, obligations, today=TODAY)
    # 50k of savings must not hide the gap: spendable stays 4200, gap still fires.
    assert result["trajectory"]["balance_now"] == 4200
    assert result["trajectory"]["savings_reserve"] == 50000
    assert result["alert_type"] == "installment_gap"


def test_overspend_detected_before_salary_day():
    # No committed payment fails, but the pace drains the balance before day-25 salary.
    profile, accounts, transactions, loans, obligations = _fixture(balance=900)
    profile["salary_day"] = 25
    loans.clear()          # no installment -> no installment gap possible
    obligations.clear()
    result = run_radar(profile, accounts, transactions, loans, obligations, today=TODAY)
    # Pace is 85/day; 900 runs out ~day 21, before the day-25 salary.
    assert result["alert_type"] == "overspend"
    assert result["gap_amount"] > 0
    assert result["trajectory"]["projected_trough"]["amount"] < 0
    assert result["trajectory"]["suggested_cuts"]
    assert result["trajectory"]["suggested_cuts"][0]["category"] == "cafes"
