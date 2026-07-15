"""Deterministic recurrence detection. Python finds WHAT recurs; the LLM only labels WHAT it is.

A recurring obligation is recognised by behaviour, not by a friendly label. Two
signals separate a real obligation from coincidental discretionary spending:

  1. Isolation by amount — a rent of 4,500 or a transfer of 1,500 is the only
     charge of that size each month. Coffee at 40-100 SAR sits in a dense crowd
     of similar amounts, so a "cluster" of it is just a sample, not an obligation.
  2. A real recurring-provider signal in the text — SADAD, EJAR, TABBY, TAMARA,
     NETFLIX. These genuinely appear in bank feeds (unlike a name like "abu
     fahad"), and they rescue small obligations (BNPL, subscriptions) whose
     amount overlaps ordinary spending.

A group is kept when it recurs monthly AND (is isolated OR carries a signal).
The LLM then labels each survivor; anything it calls flexible/one-off is dropped.
"""
from statistics import mean, median, pstdev


# A transaction joins a group when its day is within this many days of the
# group's day and its amount is within this fraction of the group's mean.
# Kept tight: a real obligation lands on almost the same day at almost the same
# amount, so a narrow window stops ordinary purchases polluting a real group.
DAY_TOLERANCE = 1
AMOUNT_TOLERANCE = 0.10

# A candidate must repeat across at least MIN_MONTHS months and average at most
# MAX_TXNS_PER_MONTH hits per month (a bill, not a spending burst).
MIN_MONTHS = 2
MAX_TXNS_PER_MONTH = 1.6

# Isolation: a group is "isolated" when it makes up at least this share of all
# expenses within +/- AMOUNT_NEIGHBORHOOD of its amount. Big fixed charges score
# ~1.0; a coffee cluster drawn from dense small spending scores low.
AMOUNT_NEIGHBORHOOD = 0.20
ISOLATION_MIN = 0.55

# Real recurring-provider signals seen in Saudi bank narratives (not friendly
# labels). Case-insensitive substring match rescues small obligations by amount.
OBLIGATION_SIGNALS = (
    "sadad", "ejar", "tabby", "tamara", "netflix", "shahid", "installment",
    "instalment", "subscription", "fin ", "auto fin", "personal fin",
    "تمارا", "تابي", "جمعية", "قسط", "إيجار", "ايجار", "تمويل", "كهرباء", "اشتراك",
)


def find_recurring_groups(transactions: list[dict]) -> list[dict]:
    """Group expense transactions that repeat at a stable amount and day of month."""
    expenses = [t for t in transactions if t.get("transaction_type") == "expense" and t.get("amount")]
    expenses.sort(key=lambda t: str(t.get("transaction_date", "")))

    groups: list[dict] = []
    for txn in expenses:
        target = _match_group(groups, txn)
        if target is None:
            target = {"txns": []}
            groups.append(target)
        target["txns"].append(txn)

    all_amounts = [abs(float(t["amount"])) for t in expenses]
    candidates = [_summarize_group(index, g["txns"]) for index, g in enumerate(groups)]
    return [c for c in candidates if _is_obligation(c, all_amounts)]


def _match_group(groups: list[dict], txn: dict) -> dict | None:
    """Find an existing group whose day and mean amount are close to this txn."""
    day = _day_of(txn)
    amount = abs(float(txn["amount"]))
    for group in groups:
        rows = group["txns"]
        group_amount = mean(abs(float(r["amount"])) for r in rows)
        group_day = median(_day_of(r) for r in rows)
        if abs(day - group_day) <= DAY_TOLERANCE and _within(amount, group_amount, AMOUNT_TOLERANCE):
            return group
    return None


def _summarize_group(index: int, rows: list[dict]) -> dict:
    """Reduce a group to the evidence the agent needs plus Python-owned numbers."""
    months = sorted({str(r.get("transaction_date", ""))[:7] for r in rows})
    amounts = [abs(float(r["amount"])) for r in rows]
    avg = mean(amounts)
    # A few distinct raw descriptions are enough context for the agent to label.
    samples = list(dict.fromkeys(str(r.get("raw_description") or r.get("merchant") or "") for r in rows))
    return {
        "group_id": f"G{index:03d}",
        "sample_descriptions": samples[:4],
        "sample_merchants": list(dict.fromkeys(
            str(r.get("merchant")) for r in rows if r.get("merchant")
        ))[:4],
        "sample_channels": sorted({str(r.get("channel")) for r in rows if r.get("channel")}),
        "monthly_amount": round(avg, 2),
        "amount_cov": round(pstdev(amounts) / avg, 3) if len(amounts) > 1 and avg > 0 else 0.0,
        "day_of_month": round(median(_day_of(r) for r in rows)),
        "months_seen": months,
        "occurrences": len(rows),
        "source_bank_codes": sorted({r.get("bank_code") for r in rows if r.get("bank_code")}),
        "transaction_ids": [r["transaction_id"] for r in rows],
    }


def _is_obligation(candidate: dict, all_amounts: list[float]) -> bool:
    """A monthly-recurring group that is either isolated by amount or carries a signal."""
    months = len(candidate["months_seen"])
    if months < MIN_MONTHS or candidate["occurrences"] / months > MAX_TXNS_PER_MONTH:
        return False
    return _has_signal(candidate["sample_descriptions"]) or _is_isolated(candidate, all_amounts)


def _has_signal(descriptions: list[str]) -> bool:
    """True when any sample description contains a real recurring-provider signal."""
    blob = " ".join(descriptions).lower()
    return any(signal in blob for signal in OBLIGATION_SIGNALS)


def _is_isolated(candidate: dict, all_amounts: list[float]) -> bool:
    """True when the group dominates the expenses near its amount (a fixed charge, not a crowd)."""
    amount = candidate["monthly_amount"]
    low, high = amount * (1 - AMOUNT_NEIGHBORHOOD), amount * (1 + AMOUNT_NEIGHBORHOOD)
    neighbors = sum(1 for a in all_amounts if low <= a <= high)
    if neighbors == 0:
        return False
    return candidate["occurrences"] / neighbors >= ISOLATION_MIN


def _day_of(txn: dict) -> int:
    """Day of month from an ISO date string, defaulting to 1 when absent."""
    raw = str(txn.get("transaction_date", ""))
    return int(raw[8:10]) if len(raw) >= 10 else 1


def _within(value: float, reference: float, tolerance: float) -> bool:
    """True when value is within tolerance (fraction) of reference."""
    if reference <= 0:
        return False
    return abs(value - reference) <= reference * tolerance
