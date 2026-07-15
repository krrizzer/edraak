"""Data-completeness layer: deterministic evidence + hooks for the LLM sufficiency judgment.

Honest split of labour:
  - Python computes FACTS: is a salary visible, do visible expenses exceed visible
    income, and how deep is the visible history.
  - The Data Sufficiency Agent (LLM) makes the JUDGMENT a rule can't: does this
    transaction picture look like a complete financial life, or is a slice of it
    clearly happening somewhere we can't see? (No bureau shortcut — under open
    banking we only know what the customer has linked.)
"""


BANK_NAMES_AR = {
    "ALINMA": "مصرف الإنماء",
    "ALRAJHI": "مصرف الراجحي",
    "SNB": "البنك الأهلي السعودي",
    "RIYAD": "بنك الرياض",
    "SAB": "البنك السعودي الأول",
}

# Demo seed data intentionally places every external row at Al Rajhi. Other
# banks remain visible in the UI. This list drives only the demo link suggestion;
# it is never passed to the AI as evidence of customer ownership.
DEMO_REQUIRED_BANKS = ["ALINMA", "ALRAJHI"]

STATUS_ENOUGH = "كافية"
STATUS_PARTIAL = "جزئية"
STATUS_INSUFFICIENT = "غير كافية"


def check_completeness(customer: dict, accounts: list[dict], transactions: list[dict],
                       loans: list[dict], connected_banks: list[str]) -> dict:
    """Deterministic pass: hard facts, blocking rules, and the unlinked-banks list."""
    findings: list[dict] = []
    blocking = False
    salary = float(customer.get("salary") or 0)

    if not _salary_visible(transactions, salary):
        blocking = True
        findings.append(_finding(
            "salary_missing", "critical",
            "لا نرى راتبك في الحسابات المرتبطة — اربط حساب الراتب أولًا، فبدونه لا يمكن بناء التوقعات."))

    if _expenses_exceed_income(transactions, salary):
        findings.append(_finding(
            "hidden_outflow", "medium",
            "مصاريفك المرئية أعلى من دخلك المرئي — يبدو أن جزءًا من حساباتك غير مرتبط."))

    months = _history_months(transactions)
    if 0 < months < 3:
        findings.append(_finding(
            "short_history", "low",
            "سجل المعاملات أقصر من ثلاثة أشهر كاملة، لذا دقة التوقعات محدودة."))

    unlinked = [b for b in DEMO_REQUIRED_BANKS if b not in {c.upper() for c in connected_banks}]
    return {
        "status": STATUS_INSUFFICIENT if blocking else (STATUS_PARTIAL if findings else STATUS_ENOUGH),
        "is_blocking": blocking,
        "connected_banks": connected_banks,
        "connected_banks_ar": [BANK_NAMES_AR.get(b, b) for b in connected_banks],
        "findings": findings,
        "suggested_banks": [{"bank_code": b, "bank_name_ar": BANK_NAMES_AR.get(b, b)} for b in unlinked],
    }


def build_evidence(customer: dict, accounts: list[dict], transactions: list[dict],
                   loans: list[dict], connected_banks: list[str]) -> dict:
    """The aggregate facts + samples the sufficiency agent reasons over. Python owns the numbers."""
    months = max(_history_months(transactions), 1)
    expenses = [t for t in transactions if t.get("transaction_type") == "expense"]
    incomes = [t for t in transactions if t.get("transaction_type") == "income"]
    by_signal: dict[str, float] = {}
    for t in expenses:
        key = t.get("merchant") or t.get("raw_description") or "unknown"
        by_signal[str(key)[:80]] = by_signal.get(str(key)[:80], 0) + abs(float(t.get("amount") or 0))

    recent = sorted(transactions, key=lambda t: str(t.get("transaction_date", "")), reverse=True)[:25]
    return {
        "declared_salary": customer.get("salary"),
        "connected_banks_ar": [BANK_NAMES_AR.get(b, b) for b in connected_banks],
        "history_months": months,
        "transactions_count": len(transactions),
        "avg_monthly_income_visible": round(sum(float(t.get("amount") or 0) for t in incomes) / months),
        "avg_monthly_expense_visible": round(sum(abs(float(t.get("amount") or 0)) for t in expenses) / months),
        "top_expense_signals": [
            {"merchant_or_description": key, "avg_monthly_amount": round(value / months)}
            for key, value in sorted(by_signal.items(), key=lambda item: -item[1])[:12]
        ],
        "visible_loans_count": len(loans),
        "visible_loan_installments": round(sum(float(l.get("monthly_installment") or 0) for l in loans)),
        "total_visible_balance": round(sum(float(a.get("balance") or 0) for a in accounts)),
        "recent_transactions_sample": [
            {"date": str(t.get("transaction_date", ""))[:10],
             "amount": t.get("amount"),
             "merchant": t.get("merchant"),
             "description": t.get("raw_description") or "",
             "channel": t.get("channel")}
            for t in recent
        ],
    }


def _salary_visible(transactions: list[dict], salary: float) -> bool:
    """True when a salary-sized income transaction exists in the linked feeds."""
    if salary <= 0:
        return False
    return any(
        t.get("transaction_type") == "income" and float(t.get("amount") or 0) >= salary * 0.7
        for t in transactions
    )


def _expenses_exceed_income(transactions: list[dict], salary: float) -> bool:
    """Persistent visible outflow above visible income hints at an unlinked account."""
    months = _history_months(transactions)
    if months == 0 or salary <= 0:
        return False
    expense = sum(abs(float(t.get("amount") or 0)) for t in transactions if t.get("transaction_type") == "expense")
    income = sum(float(t.get("amount") or 0) for t in transactions if t.get("transaction_type") == "income")
    # Compare monthly averages; a 20% overshoot is beyond normal savings drawdown.
    return (expense / months) > (income / months) * 1.2 if income > 0 else expense > 0


def _history_months(transactions: list[dict]) -> int:
    """Count of distinct year-months present in the transaction history."""
    return len({str(t.get("transaction_date", ""))[:7] for t in transactions if t.get("transaction_date")})


def _finding(code: str, severity: str, message_ar: str) -> dict:
    return {"code": code, "severity": severity, "message_ar": message_ar}
