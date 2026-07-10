"""Recurrence detection tests: obligations are found by behaviour, not by text."""
from app.functions.recurrence import find_recurring_groups


def _txn(txn_id, month, day, amount, desc, bank="SNB"):
    return {
        "transaction_id": txn_id,
        "transaction_date": f"2026-{month:02d}-{day:02d}",
        "amount": amount,
        "raw_description": desc,
        "bank_code": bank,
        "transaction_type": "expense",
    }


def test_stable_amount_and_day_across_months_is_one_group():
    # Jamiya: text varies every month, but amount and day are stable.
    txns = [
        _txn("t1", 4, 5, -1000, "حوالة داخلية - جمعية شهر رجب"),
        _txn("t2", 5, 5, -1000, "حوالة - جمعية الحي"),
        _txn("t3", 6, 6, -1000, "تحويل جمعية"),
    ]
    groups = find_recurring_groups(txns)
    assert len(groups) == 1
    assert groups[0]["monthly_amount"] == 1000
    assert groups[0]["day_of_month"] == 5
    assert len(groups[0]["transaction_ids"]) == 3


def test_two_different_plans_stay_separate():
    # Two BNPL plans: different amounts and days -> two groups, not merged by "TABBY".
    txns = [
        _txn("a1", 4, 12, -450, "POS TABBY* PAYMENT RUH"),
        _txn("a2", 5, 12, -450, "TABBY *INSTALMENT 2 OF 4"),
        _txn("b1", 4, 20, -300, "POS TABBY PAYMENT"),
        _txn("b2", 5, 20, -300, "TABBY *3 OF 6"),
    ]
    groups = find_recurring_groups(txns)
    amounts = sorted(g["monthly_amount"] for g in groups)
    assert amounts == [300, 450]


def test_one_off_and_flexible_spending_are_not_obligations():
    # A single purchase and many same-month coffees must not become obligations.
    txns = [
        _txn("one", 4, 9, -1200, "POS ELECTRONICS STORE"),
        _txn("c1", 5, 3, -80, "POS BARNS COFFEE"),
        _txn("c2", 5, 11, -85, "POS BARNS COFFEE"),
        _txn("c3", 5, 19, -78, "POS BARNS COFFEE"),
        _txn("c4", 5, 26, -82, "POS BARNS COFFEE"),
    ]
    assert find_recurring_groups(txns) == []
