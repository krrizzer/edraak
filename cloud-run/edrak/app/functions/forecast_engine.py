"""Month-by-month cross-bank cash-flow projection. Pure Python, no LLM, fully testable."""
from dataclasses import asdict, dataclass


# Obligation types from the Transaction Intelligence Agent that count as
# committed monthly outflow. loan_installment_other_bank is EXCLUDED because
# the loans table already carries every cross-bank loan; counting the detected
# transaction pattern too would double the installment.
COMMITTED_OBLIGATION_TYPES = {"bnpl_installment", "jamiya", "family_support", "rent", "subscription"}

# Salary day spread (std dev in days) above which we flag timing variance.
SALARY_VARIANCE_FLAG_DAYS = 2.5


@dataclass
class MonthPoint:
    """One projected month. month=1 is the first full month after today."""
    month: int
    income: float
    committed: float
    new_commitment: float
    flexible: float
    buffer: float
    # Honest uncertainty band around buffer, from the customer's own spending volatility.
    buffer_low: float
    buffer_high: float
    obligation_ratio: float
    projected_savings: float
    events: list[dict]


@dataclass
class ForecastResult:
    """The full projection plus the summary numbers the verdict rules read."""
    months: list[MonthPoint]
    first_shortfall_month: int | None
    first_shortfall_amount: float | None
    min_buffer_month: int
    min_buffer_value: float
    months_of_savings_cover: float
    obligation_ratio_now: float
    obligation_ratio_peak: float
    obligation_ratio_month_12: float
    stress_events: list[dict]
    salary_timing_variance: bool

    def to_dict(self) -> dict:
        """Serialize for the API response and BigQuery storage."""
        return asdict(self)


def build_forecast(profile: dict, loans: list[dict], obligations: list[dict],
                   new_installment: float = 0.0, horizon: int = 12,
                   start_offset: int = 0, duration_months: int | None = None,
                   down_payment: float = 0.0) -> ForecastResult:
    """Project income, committed outflow, and buffer for each of the next `horizon` months.

    start_offset shifts the whole simulation N months into the future — used by the
    verdict rules to answer "if the customer waits N months, is the plan clean?".
    duration_months stops the new installment once the loan is paid off; down_payment
    is spent up front, so it lowers the starting savings balance.
    """
    salary = float(profile.get("salary") or 0)
    flexible = float(profile.get("avg_flexible_spending") or 0)
    volatility = round(float(profile.get("monthly_spending_std") or 0))
    savings = float(profile.get("total_balance") or 0) - float(down_payment or 0)
    items = _committed_items(loans, obligations)

    months: list[MonthPoint] = []
    for m in range(1, horizon + 1):
        shifted = m + start_offset
        committed = sum(item["amount"] for item in items if _item_active(item, shifted))
        new_commitment = new_installment if (duration_months is None or m <= duration_months) else 0.0
        buffer = round(salary - committed - new_commitment - flexible)
        ratio = _ratio(committed + new_commitment, salary)
        savings = round(savings + buffer)
        months.append(MonthPoint(
            month=m,
            income=salary,
            committed=round(committed),
            new_commitment=round(new_commitment),
            flexible=round(flexible),
            buffer=buffer,
            buffer_low=buffer - volatility,
            buffer_high=buffer + volatility,
            obligation_ratio=ratio,
            projected_savings=savings,
            events=_month_events(items, shifted),
        ))

    return _summarize(months, profile, items, new_installment, start_offset)


def _summarize(months: list[MonthPoint], profile: dict, items: list[dict],
               new_installment: float, start_offset: int) -> ForecastResult:
    """Reduce the monthly rows to the summary numbers the verdict rules need."""
    salary = float(profile.get("salary") or 0)
    shortfalls = [p for p in months if p.buffer < 0]
    worst = min(months, key=lambda p: p.buffer)
    worst_outflow = worst.committed + worst.new_commitment + worst.flexible
    cover = round(worst.projected_savings / worst_outflow, 2) if worst_outflow > 0 else 99.0

    committed_now = sum(item["amount"] for item in items if _item_active(item, 1 + start_offset))
    variance_days = float(profile.get("salary_timing_variance_days") or 0)

    return ForecastResult(
        months=months,
        first_shortfall_month=shortfalls[0].month if shortfalls else None,
        first_shortfall_amount=abs(shortfalls[0].buffer) if shortfalls else None,
        min_buffer_month=worst.month,
        min_buffer_value=worst.buffer,
        months_of_savings_cover=max(cover, 0.0),
        obligation_ratio_now=_ratio(committed_now, salary),
        obligation_ratio_peak=max(p.obligation_ratio for p in months),
        obligation_ratio_month_12=months[min(11, len(months) - 1)].obligation_ratio,
        stress_events=_stress_events(months, items, start_offset),
        salary_timing_variance=variance_days > SALARY_VARIANCE_FLAG_DAYS,
    )


def _committed_items(loans: list[dict], obligations: list[dict]) -> list[dict]:
    """Merge loans (all banks) and detected obligations into one committed-outflow list."""
    items = []
    for loan in loans:
        if loan.get("status") != "active":
            continue
        items.append({
            "label": f"{loan.get('loan_type', 'loan')}@{loan.get('bank_code', '?')}",
            "amount": float(loan.get("monthly_installment") or 0),
            "remaining": loan.get("remaining_months"),
            "kind": "loan",
        })
    for ob in obligations:
        if not ob.get("is_committed", True):
            continue
        if ob.get("obligation_type") not in COMMITTED_OBLIGATION_TYPES:
            continue
        items.append({
            "label": ob.get("counterparty") or ob["obligation_type"],
            "amount": float(ob.get("monthly_amount") or 0),
            "remaining": ob.get("remaining_months"),
            "kind": ob["obligation_type"],
        })
    return items


def _item_active(item: dict, month: int) -> bool:
    """An item pays in `month` while it still has remaining installments (None = ongoing)."""
    remaining = item.get("remaining")
    return remaining is None or month <= remaining


def _month_events(items: list[dict], month: int) -> list[dict]:
    """Annotate the month where an obligation just ended — the UI marks these."""
    return [
        {"type": "obligation_released", "label": item["label"], "amount": item["amount"], "kind": item["kind"]}
        for item in items
        if item.get("remaining") is not None and item["remaining"] == month - 1 and item["remaining"] >= 0
    ]


def _stress_events(months: list[MonthPoint], items: list[dict], start_offset: int) -> list[dict]:
    """Tag every shortfall month with a deterministic cause. Arabic prose comes from Agent 2."""
    events = []
    for point in [p for p in months if p.buffer < 0]:
        shifted = point.month + start_offset
        bnpl = [i for i in items if i["kind"] == "bnpl_installment" and _item_active(i, shifted)]
        ending = [i for i in items
                  if i.get("remaining") is not None and shifted <= i["remaining"] <= shifted + 2]
        if ending:
            cause = "temporary_overlap"
        elif bnpl:
            cause = "bnpl_stacking"
        else:
            cause = "structural_overcommitment"
        events.append({
            "month": point.month,
            "cause": cause,
            "gap": abs(point.buffer),
            "ending_soon": [i["label"] for i in ending],
        })
    return events


def _ratio(monthly_obligations: float, salary: float) -> float:
    """Obligation ratio as a percentage of salary; 100 when there is no salary."""
    if salary <= 0:
        return 100.0
    return round(monthly_obligations / salary * 100, 1)
