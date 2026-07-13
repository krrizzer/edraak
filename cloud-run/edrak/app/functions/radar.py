"""Financial Radar: deterministic current-month trajectory and gap detection. No LLM here."""
import logging
from calendar import monthrange
from datetime import date

from app.functions.forecast_engine import COMMITTED_OBLIGATION_TYPES


logger = logging.getLogger("edraak.radar")

# Arabic labels for spending categories shown in alerts and the trajectory panel.
CATEGORY_LABELS_AR = {
    "cafes": "المقاهي",
    "restaurants": "المطاعم",
    "groceries": "التموينات",
    "shopping": "التسوق",
    "entertainment": "الترفيه",
    "fuel": "الوقود",
    "transport": "المواصلات",
    "misc": "متفرقات",
    "housing": "السكن",
    "bills": "الفواتير",
    "uncategorized": "غير مصنف",
}

# Below this many elapsed days the month-to-date pace is too noisy, so we fall
# back to the trailing baseline pace instead of extrapolating two data points.
MIN_DAYS_FOR_PACE = 3

# Baselines smaller than this (SAR, same-day window) cannot name a cause credibly.
MIN_BASELINE_FOR_CAUSE = 50


def run_radar(profile: dict, accounts: list[dict], transactions: list[dict],
              loans: list[dict], obligations: list[dict], today: date | None = None) -> dict:
    """Project the current month against a real budget and detect trouble early.

    Two detections, in priority order:
      1. installment_gap — the projected balance can't cover a committed payment date.
      2. overspend — no payment fails, but the spending pace drives the SPENDABLE
         balance below zero before the month ends (usually before salary day).
    Savings accounts are a reserve, not a budget — they are reported separately
    and never counted as spendable.
    """
    today = today or date.today()
    spendable = sum(float(a.get("balance") or 0) for a in accounts
                    if a.get("account_type", "current") != "savings")
    savings_reserve = sum(float(a.get("balance") or 0) for a in accounts
                          if a.get("account_type") == "savings")
    flexible = _flexible_expenses(transactions, obligations, loans)
    categories = _category_pace(flexible, today)
    daily_pace = _daily_pace(flexible, today)
    payments = _upcoming_payments(obligations, loans, today)
    salary_day, salary = _pending_salary(profile, transactions, today)

    gap = _find_gap(spendable, daily_pace, payments, salary_day, salary, today)
    trough, projected_eom = _project_month(spendable, daily_pace, payments, salary_day, salary, today)
    flexible_budget = round(float(profile.get("avg_flexible_spending") or 0))
    flexible_used = round(_mtd_total(flexible, today))
    committed_month = round(sum(p["amount"] for p in payments))
    cause = _cause_category(categories)
    suggested_cuts = _suggested_cuts(categories, trough, today)

    if gap is not None:
        alert_type = "installment_gap"
    elif trough["amount"] < 0:
        alert_type = "overspend"
    else:
        alert_type = "on_track"

    trajectory = {
        "as_of": today.isoformat(),
        "balance_now": round(spendable),
        "savings_reserve": round(savings_reserve),
        "monthly_budget": flexible_budget + committed_month,
        "flexible_budget": flexible_budget,
        "flexible_used_mtd": flexible_used,
        "budget_used_pct": round(flexible_used / flexible_budget * 100) if flexible_budget > 0 else 0,
        "daily_flexible_pace": round(daily_pace),
        "projected_eom_balance": projected_eom,
        "projected_trough": trough,
        "expected_salary_day": salary_day,
        "categories": categories,
        "upcoming_payments": payments,
        "suggested_cuts": suggested_cuts,
    }
    logger.info(
        "flow.radar.detection customer_id=%s alert_type=%s pace=%s trough=%s payments=%s message=Radar trajectory computed",
        profile.get("customer_id"), alert_type, round(daily_pace), trough["amount"], len(payments),
    )
    return {
        "has_gap": gap is not None,
        "alert_type": alert_type,
        "gap_amount": gap["amount"] if gap else (abs(trough["amount"]) if alert_type == "overspend" else None),
        "gap_date": gap["date"] if gap else (trough["date"] if alert_type == "overspend" else None),
        "cause_category": cause if alert_type != "on_track" else None,
        "trajectory": trajectory,
    }


def _project_month(spendable: float, daily_pace: float, payments: list[dict],
                   salary_day: int | None, salary: float, today: date) -> tuple[dict, int]:
    """Simulate the spendable balance day by day to month end; return (trough, eom)."""
    days_in_month = monthrange(today.year, today.month)[1]
    balance = spendable
    lowest = {"amount": round(balance), "date": today.isoformat()}
    for day in range(today.day + 1, days_in_month + 1):
        balance -= daily_pace
        if salary_day is not None and day == salary_day:
            balance += salary
        balance -= sum(p["amount"] for p in payments if p["day"] == day)
        if balance < lowest["amount"]:
            lowest = {"amount": round(balance), "date": date(today.year, today.month, day).isoformat()}
    return lowest, round(balance)


def _mtd_total(flexible: list[dict], today: date) -> float:
    """Total flexible spend so far this month."""
    current = today.isoformat()[:7]
    return sum(abs(float(t.get("amount") or 0)) for t in flexible
               if str(t.get("transaction_date", "")).startswith(current))


def _suggested_cuts(categories: list[dict], trough: dict, today: date) -> list[dict]:
    """Deterministic advice input: which accelerating categories can cover the shortfall.

    For each category spending above its baseline, the recoverable amount is the
    excess pace projected over the remaining days. The agent phrases the advice;
    these numbers are Python's.
    """
    shortfall = max(-trough["amount"], 0)
    if shortfall == 0:
        return []
    days_left = monthrange(today.year, today.month)[1] - today.day
    elapsed = max(today.day, 1)
    cuts = []
    for row in categories:
        if row["deviation_pct"] <= 0 or row["baseline_mtd"] < MIN_BASELINE_FOR_CAUSE:
            continue
        excess_daily = (row["mtd"] - row["baseline_mtd"]) / elapsed
        recoverable = round(excess_daily * days_left)
        if recoverable > 0:
            cuts.append({"category": row["category"], "label_ar": row["label_ar"],
                         "recoverable": recoverable})
    return sorted(cuts, key=lambda c: -c["recoverable"])[:3]


def _flexible_expenses(transactions: list[dict], obligations: list[dict], loans: list[dict]) -> list[dict]:
    """Expenses that are not matched to a committed obligation or loan installment."""
    committed = [
        {"amount": abs(float(ob.get("monthly_amount") or 0)), "day": int(ob.get("day_of_month") or 0)}
        for ob in obligations
        if ob.get("is_committed", True) and ob.get("obligation_type") in COMMITTED_OBLIGATION_TYPES
    ] + [
        {"amount": abs(float(l.get("monthly_installment") or 0)), "day": _loan_day(l)}
        for l in loans if l.get("status") == "active"
    ]
    return [
        t for t in transactions
        if t.get("transaction_type") == "expense" and not _matches_committed(t, committed)
    ]


def _matches_committed(txn: dict, committed: list[dict]) -> bool:
    """Match a transaction to a committed item by amount (±10%) and day (±1).

    The day window is tight on purpose: obligation days come from the median of
    the actual history, and a loose window lets ordinary purchases steal the
    slot of a similarly sized bill, which corrupts the flexible pace.
    """
    amount = abs(float(txn.get("amount") or 0))
    day = int(str(txn.get("transaction_date", "--------01"))[8:10] or 1)
    for item in committed:
        if item["amount"] <= 0:
            continue
        if abs(amount - item["amount"]) <= item["amount"] * 0.10 and abs(day - item["day"]) <= 1:
            return True
    return False


def _category_pace(flexible: list[dict], today: date) -> list[dict]:
    """Month-to-date spend per category vs the same day-window average of 3 prior months."""
    current = today.isoformat()[:7]
    prior = sorted({
        str(t["transaction_date"])[:7] for t in flexible
        if str(t.get("transaction_date", ""))[:7] < current
    }, reverse=True)[:3]

    rows = []
    for category in sorted({_category(t) for t in flexible}):
        mtd = _window_total(flexible, category, [current], today.day)
        baseline = _window_total(flexible, category, prior, today.day) / max(len(prior), 1)
        deviation = round((mtd - baseline) / baseline * 100) if baseline > 0 else 0
        rows.append({
            "category": category,
            "label_ar": CATEGORY_LABELS_AR.get(category, category),
            "mtd": round(mtd),
            "baseline_mtd": round(baseline),
            "deviation_pct": deviation,
        })
    return sorted(rows, key=lambda r: r["deviation_pct"], reverse=True)


def _window_total(flexible: list[dict], category: str, months: list[str], max_day: int) -> float:
    """Total spend for one category inside the first max_day days of the given months."""
    return sum(
        abs(float(t.get("amount") or 0))
        for t in flexible
        if _category(t) == category
        and str(t.get("transaction_date", ""))[:7] in months
        and int(str(t["transaction_date"])[8:10]) <= max_day
    )


def _daily_pace(flexible: list[dict], today: date) -> float:
    """Current daily flexible-spend rate; falls back to baseline early in the month."""
    current = today.isoformat()[:7]
    mtd = sum(abs(float(t["amount"])) for t in flexible if str(t.get("transaction_date", "")).startswith(current))
    if today.day >= MIN_DAYS_FOR_PACE and mtd > 0:
        return mtd / today.day
    prior = sorted({str(t["transaction_date"])[:7] for t in flexible
                    if str(t.get("transaction_date", ""))[:7] < current}, reverse=True)[:3]
    if not prior:
        return 0.0
    total = sum(abs(float(t["amount"])) for t in flexible if str(t["transaction_date"])[:7] in prior)
    return total / len(prior) / 30


def _upcoming_payments(obligations: list[dict], loans: list[dict], today: date) -> list[dict]:
    """Committed payments still due this month, sorted by day."""
    days_in_month = monthrange(today.year, today.month)[1]
    payments = []
    for ob in obligations:
        if not ob.get("is_committed", True) or ob.get("obligation_type") not in COMMITTED_OBLIGATION_TYPES:
            continue
        day = int(ob.get("day_of_month") or 0)
        if today.day < day <= days_in_month:
            payments.append({"label": ob.get("counterparty") or ob["obligation_type"],
                             "kind": ob["obligation_type"],
                             "amount": abs(float(ob.get("monthly_amount") or 0)), "day": day})
    for loan in loans:
        if loan.get("status") != "active" or (loan.get("remaining_months") or 0) < 1:
            continue
        day = _loan_day(loan)
        if today.day < day <= days_in_month:
            payments.append({"label": f"{loan.get('loan_type', 'loan')}@{loan.get('bank_code', '?')}",
                             "kind": "loan",
                             "amount": abs(float(loan.get("monthly_installment") or 0)), "day": day})
    return sorted(payments, key=lambda p: p["day"])


def _pending_salary(profile: dict, transactions: list[dict], today: date) -> tuple[int | None, float]:
    """Return (salary_day, amount) if this month's salary has not landed yet."""
    salary = float(profile.get("salary") or 0)
    salary_day = int(profile.get("salary_day") or 25)
    current = today.isoformat()[:7]
    received = any(
        t.get("transaction_type") == "income"
        and str(t.get("transaction_date", "")).startswith(current)
        and float(t.get("amount") or 0) >= salary * 0.7
        for t in transactions
    )
    if received or salary_day <= today.day:
        return None, 0.0
    return salary_day, salary


def _find_gap(balance_now: float, daily_pace: float, payments: list[dict],
              salary_day: int | None, salary: float, today: date) -> dict | None:
    """Walk each upcoming payment date and check the projected balance covers it."""
    for payment in payments:
        days_until = payment["day"] - today.day
        income = salary if salary_day is not None and salary_day <= payment["day"] else 0.0
        paid_before = sum(p["amount"] for p in payments if p["day"] < payment["day"])
        available = balance_now + income - paid_before - daily_pace * days_until
        if available < payment["amount"]:
            gap_date = date(today.year, today.month, payment["day"])
            return {"amount": round(payment["amount"] - available), "date": gap_date.isoformat(),
                    "payment": payment}
    return None


def _cause_category(categories: list[dict]) -> dict | None:
    """The category whose acceleration best explains the gap: biggest positive deviation.

    Named categories win over "uncategorized" because only a named cause can carry
    an actionable fix ("cut cafe spending this week").
    """
    candidates = [c for c in categories
                  if c["deviation_pct"] > 0 and c["baseline_mtd"] >= MIN_BASELINE_FOR_CAUSE]
    named = [c for c in candidates if c["category"] != "uncategorized"]
    if named:
        return named[0]
    return candidates[0] if candidates else None


def _category(txn: dict) -> str:
    return txn.get("category") or "uncategorized"


def _loan_day(loan: dict) -> int:
    """Installment day of month, taken from the first installment date."""
    raw = str(loan.get("first_installment_date") or "")
    return int(raw[8:10]) if len(raw) >= 10 else 27
