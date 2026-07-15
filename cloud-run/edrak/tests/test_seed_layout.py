"""Demo seed guarantees: one external link and no trusted source category."""
from collections import defaultdict
from datetime import date

from app.data.seed.generate_seed_data import HOST_BANK, generate_all


def test_every_external_row_is_consolidated_under_al_rajhi():
    tables = generate_all(today=date(2026, 7, 10))
    customer_ids = {row["customer_id"] for row in tables["customers"]}

    for table_name in ("accounts", "transactions", "loans"):
        external_codes = {
            row["bank_code"]
            for row in tables[table_name]
            if row["bank_code"] != HOST_BANK
        }
        assert external_codes <= {"ALRAJHI"}

    customers_with_al_rajhi = {
        row["customer_id"]
        for row in tables["accounts"]
        if row["bank_code"] == "ALRAJHI"
    }
    assert customers_with_al_rajhi == customer_ids


def test_source_transactions_have_no_category_column():
    tables = generate_all(today=date(2026, 7, 10))
    assert tables["transactions"]
    assert all("category" not in row for row in tables["transactions"])


def test_five_customers_have_complete_referentially_valid_bank_worlds():
    tables = generate_all(today=date(2026, 7, 14))
    assert {row["customer_id"] for row in tables["customers"]} == {
        "CUST001", "CUST002", "CUST003", "CUST004", "CUST005",
    }
    accounts = {row["account_id"]: row for row in tables["accounts"]}
    for customer in tables["customers"]:
        customer_id = customer["customer_id"]
        customer_accounts = [a for a in accounts.values() if a["customer_id"] == customer_id]
        assert any(a["bank_code"] == "ALINMA" and a["is_primary"] for a in customer_accounts)
        assert any(a["bank_code"] == "ALINMA" and a["account_type"] == "savings" for a in customer_accounts)
        assert any(a["bank_code"] == "ALRAJHI" and a["account_type"] == "current" for a in customer_accounts)
    for txn in tables["transactions"]:
        account = accounts[txn["account_id"]]
        assert (account["customer_id"], account["bank_code"]) == (
            txn["customer_id"], txn["bank_code"],
        )


def test_customer_spending_is_affordable_but_financially_distinct():
    tables = generate_all(today=date(2026, 7, 14))
    salaries = {row["customer_id"]: row["salary"] for row in tables["customers"]}
    monthly_expenses = defaultdict(lambda: defaultdict(float))
    for txn in tables["transactions"]:
        # Six completed months only; current MTD pace is intentionally abnormal
        # for the radar personas and should not distort affordability validation.
        if txn["transaction_date"] < "2026-07-01" and txn["amount"] < 0:
            monthly_expenses[txn["customer_id"]][txn["transaction_date"][:7]] -= txn["amount"]

    ratios = {}
    for customer_id, months in monthly_expenses.items():
        average = sum(months.values()) / len(months)
        ratios[customer_id] = average / salaries[customer_id]
        assert 0.50 <= ratios[customer_id] <= 1.00

    # Sara is deliberately the strongest saver; Fahad is the tightest normal
    # monthly budget; Noura remains stressed but plausible rather than insolvent.
    assert ratios["CUST002"] < ratios["CUST003"] < ratios["CUST004"] < ratios["CUST001"]


def test_life_events_and_payment_channels_look_like_raw_bank_data():
    tables = generate_all(today=date(2026, 7, 14))
    descriptions = "\n".join(row["raw_description"] for row in tables["transactions"])
    for evidence in (
        "PERFORMANCE BONUS", "HOLIDAY PACKAGE", "CAR REPAIR",
        "OVERTIME PAYMENT", "MOTOR INSURANCE",
    ):
        assert evidence in descriptions
    assert {row["channel"] for row in tables["transactions"]} >= {
        "transfer", "sadad", "atm", "ecommerce", "pos", "card",
    }


def test_iban_generation_is_stable_across_runs():
    first = generate_all(today=date(2026, 7, 14))["accounts"]
    second = generate_all(today=date(2026, 7, 14))["accounts"]
    assert [(row["account_id"], row["iban"]) for row in first] == [
        (row["account_id"], row["iban"]) for row in second
    ]
