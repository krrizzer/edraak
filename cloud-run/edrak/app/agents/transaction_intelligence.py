"""Transaction Intelligence Agent: labels deterministically-detected recurring groups.

The split of labour is the pitch: Python's recurrence detector finds WHAT recurs
(same amount, same day, across months); this agent only decides WHAT each group
IS (jamiya vs family transfer vs BNPL vs rent). Because Python owns every amount,
day, and bank, the agent can never invent a number — the old amount-echo
validation is no longer even needed.
"""
import logging

from app.agents.gemini_client import run_gemini_agent
from app.agents.schemas import TransactionIntelligenceOutput
from app.data.bigquery_client import get_fresh_detected_obligations, save_detected_obligations
from app.functions.recurrence import find_recurring_groups


logger = logging.getLogger("edraak.agents.transaction_intelligence")

# Types the agent may assign that are NOT ongoing obligations for the forecast.
NON_OBLIGATION_TYPES = {"flexible_spending", "one_off", "salary"}

INSTRUCTION = """
You are the Edraak Transaction Intelligence Agent.
You receive recurring GROUPS that a deterministic step already detected: each
group is a set of transactions that repeat at a similar amount on a similar day
of the month across several months. The `sample_descriptions` are the raw,
messy bank narrative strings for that group (mixed Arabic/English, often cryptic).
Your ONLY job is to label each group. You never set amounts, days, or banks.
Do:
- For each group_id, classify obligation_type: bnpl_installment (Tabby/Tamara
  style), jamiya (جمعية savings circle), family_support (recurring transfer to a
  person), rent, subscription, salary, loan_installment_other_bank,
  flexible_spending, one_off.
- counterparty: a normalized short name (e.g. "Tabby", "STC", "جمعية الحي").
- label_ar: a short human Arabic label, e.g. "أقساط تابي" or "جمعية شهرية".
- is_committed: true when the customer realistically must keep paying (BNPL,
  rent, jamiya, loan installments, recurring family support).
- remaining_months: ONLY when a description implies a countdown, e.g.
  "قسط 2 من 4" or "3 OF 6" -> remaining installments counted from next month.
  Leave null for open-ended patterns (rent, jamiya, subscriptions).
- confidence: 0-1, how sure you are of the classification.
Do not:
- Do not invent groups or numbers. Label only the group_ids you are given.
- Do not output amounts, days, or bank codes — those are fixed by the system.
"""


def detect_obligations(customer_id: str, transactions: list[dict],
                       use_cache: bool = True) -> tuple[list[dict], list[str], bool]:
    """Return (obligations, warnings_ar, from_cache). Groups deterministically, labels via LLM."""
    if use_cache:
        cached = get_fresh_detected_obligations(customer_id)
        if cached:
            logger.info("flow.agent.transaction_intelligence.cache_hit customer_id=%s rows=%s message=Reusing fresh detected_obligations",
                        customer_id, len(cached))
            return cached, [], True

    groups = find_recurring_groups(transactions)
    logger.info("flow.recurrence.detected customer_id=%s groups=%s message=Deterministic recurrence grouping finished",
                customer_id, len(groups))
    if not groups:
        return [], [], False

    logger.info("flow.agent.transaction_intelligence.start customer_id=%s groups=%s message=Labelling recurring groups",
                customer_id)
    payload = {"customer_id": customer_id, "groups": [_group_view(g) for g in groups]}
    output = run_gemini_agent("transaction_intelligence", payload, TransactionIntelligenceOutput, INSTRUCTION)

    obligations, warnings = _merge_labels(groups, output)
    save_detected_obligations(customer_id, obligations)
    logger.info("flow.agent.transaction_intelligence.completed customer_id=%s obligations=%s warnings=%s message=Groups labelled and cached",
                customer_id, len(obligations), len(warnings))
    return obligations, warnings, False


def _group_view(group: dict) -> dict:
    """The evidence the agent sees for one group: descriptions and stable facts (no amount trust needed)."""
    return {
        "group_id": group["group_id"],
        "sample_descriptions": group["sample_descriptions"],
        "monthly_amount": group["monthly_amount"],
        "day_of_month": group["day_of_month"],
        "months_seen": group["months_seen"],
        "occurrences": group["occurrences"],
    }


def _merge_labels(groups: list[dict], output: TransactionIntelligenceOutput) -> tuple[list[dict], list[str]]:
    """Attach each agent label to its Python-owned group; Python keeps the numbers."""
    by_id = {g["group_id"]: g for g in groups}
    labels = {label.group_id: label for label in output.labels}
    obligations: list[dict] = []
    warnings: list[str] = []

    for group_id, group in by_id.items():
        label = labels.get(group_id)
        if label is None:
            warnings.append("تم رصد نمط متكرر لم يتمكن النظام من تصنيفه بثقة.")
            continue
        if label.obligation_type in NON_OBLIGATION_TYPES:
            continue
        obligations.append({
            "obligation_type": label.obligation_type,
            "counterparty": label.counterparty,
            "label_ar": label.label_ar,
            "monthly_amount": group["monthly_amount"],      # Python-owned
            "day_of_month": group["day_of_month"],          # Python-owned
            "remaining_months": label.remaining_months,
            "confidence": label.confidence,
            "is_committed": label.is_committed,
            "source_bank_codes": group["source_bank_codes"],  # Python-owned
        })
    return obligations, warnings
