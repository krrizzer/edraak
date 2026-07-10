"""Derive the cross-bank user profile row from accounts, transactions, loans, and detected obligations."""
import logging
from datetime import date, datetime, timezone
from statistics import median, pstdev

from app.functions.forecast_engine import COMMITTED_OBLIGATION_TYPES


logger = logging.getLogger("edraak.profile")

# How many FULL past months feed the spending averages. The current month is
# excluded because it is incomplete and would bias the averages down.
SPENDING_LOOKBACK_MONTHS = 3


def build_user_profile(customer: dict, accounts: list[dict], transactions: list[dict],
                       loans: list[dict], obligations: list[dict],
                       today: date | None = None) -> dict:
    """Build one user_profiles row of cross-bank aggregates. Pure Python."""
    today = today or date.today()
    salary = round(float(customer.get("salary") or 0))
    active_loans = [l for l in loans if l.get("status") == "active"]
    installments = round(sum(float(l.get("monthly_installment") or 0) for l in active_loans))

    committed_obligations = round(sum(
        float(ob.get("monthly_amount") or 0)
        for ob in obligations
        if ob.get("is_committed", True) and ob.get("obligation_type") in COMMITTED_OBLIGATION_TYPES
    ))
    avg_spending = _avg_monthly_spending(transactions, today)
    # DESIGN NOTE: flexible = total average spending minus everything committed.
    # Deterministic and immune to the unreliable category column; small drift in
    # variable bills lands in "flexible", which is the conservative direction.
    avg_flexible = max(avg_spending - committed_obligations - installments, 0)

    salary_days = _salary_days(transactions, salary)
    profile = {
        "customer_id": customer["customer_id"],
        "ar_name": customer.get("ar_name"),
        "en_name": customer.get("en_name"),
        "salary": salary,
        "salary_day": round(median(salary_days)) if salary_days else 25,
        "salary_timing_variance_days": round(pstdev(salary_days), 2) if len(salary_days) > 1 else 0.0,
        "total_balance": round(sum(float(a.get("balance") or 0) for a in accounts)),
        "banks_count": len({a.get("bank_code") for a in accounts if a.get("bank_code")}),
        "active_loans_count": len(active_loans),
        "total_remaining_loans": round(sum(float(l.get("remaining_amount") or 0) for l in active_loans)),
        "monthly_loan_installments": installments,
        "avg_monthly_spending": avg_spending,
        "avg_flexible_spending": avg_flexible,
        "monthly_spending_std": _monthly_spending_std(transactions, today),
        "profile_generated_at": datetime.now(timezone.utc).isoformat(),
    }
    logger.info(
        "flow.profile.built customer_id=%s banks=%s balance=%s flexible=%s message=Cross-bank profile derived",
        customer["customer_id"], profile["banks_count"], profile["total_balance"], avg_flexible,
    )
    return profile


def _avg_monthly_spending(transactions: list[dict], today: date) -> int:
    """Average monthly expense total over the lookback window of full months."""
    current_month = today.isoformat()[:7]
    month_keys = sorted({
        str(t.get("transaction_date", ""))[:7]
        for t in transactions
        if t.get("transaction_type") == "expense" and str(t.get("transaction_date", ""))[:7] != current_month
    }, reverse=True)[:SPENDING_LOOKBACK_MONTHS]
    if not month_keys:
        return 0
    total = sum(
        abs(float(t.get("amount") or 0))
        for t in transactions
        if t.get("transaction_type") == "expense" and str(t.get("transaction_date", ""))[:7] in month_keys
    )
    return round(total / len(month_keys))


def _monthly_spending_std(transactions: list[dict], today: date) -> int:
    """Std dev of total monthly expense across full past months — the forecast band width."""
    current_month = today.isoformat()[:7]
    totals: dict[str, float] = {}
    for t in transactions:
        month = str(t.get("transaction_date", ""))[:7]
        if t.get("transaction_type") != "expense" or not month or month == current_month:
            continue
        totals[month] = totals.get(month, 0) + abs(float(t.get("amount") or 0))
    values = list(totals.values())
    return round(pstdev(values)) if len(values) > 1 else 0


def _salary_days(transactions: list[dict], salary: float) -> list[int]:
    """Days of month when salary-sized income landed — the timing-variance signal."""
    if salary <= 0:
        return []
    return [
        int(str(t["transaction_date"])[8:10])
        for t in transactions
        if t.get("transaction_type") == "income"
        and t.get("transaction_date")
        and float(t.get("amount") or 0) >= salary * 0.7
    ]
