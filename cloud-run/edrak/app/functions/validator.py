"""Deterministic input validation. Replaces the old Validation Agent — an `if` is cheaper than an LLM."""


def validate_inputs(customer: dict, accounts: list[dict], transactions: list[dict],
                    loans: list[dict], decision_input: dict | None = None) -> dict:
    """Check data completeness and consistency; return warnings and blocking errors in Arabic."""
    warnings: list[str] = []
    blocking: list[str] = []
    customer_id = customer.get("customer_id", "")

    if not customer.get("salary") or customer["salary"] <= 0:
        blocking.append("لا يوجد راتب مسجل للعميل، ولا يمكن بناء التوقعات بدونه.")
    if not accounts:
        blocking.append("لا توجد حسابات بنكية مربوطة عبر الخدمات المصرفية المفتوحة.")
    if not transactions:
        blocking.append("لا يوجد سجل معاملات، ولا يمكن تحليل الالتزامات بدونه.")

    for label, rows in (("المعاملات", transactions), ("القروض", loans), ("الحسابات", accounts)):
        mismatched = [r for r in rows if r.get("customer_id") != customer_id]
        if mismatched:
            blocking.append(f"بعض سجلات {label} لا تخص هذا العميل ({len(mismatched)} سجل).")

    months = {str(t.get("transaction_date", ""))[:7] for t in transactions if t.get("transaction_date")}
    if 0 < len(months) < 4:
        warnings.append("سجل المعاملات أقصر من ثلاثة أشهر كاملة، لذا دقة التوقعات محدودة.")

    missing_desc = [t for t in transactions if not t.get("raw_description")]
    if transactions and len(missing_desc) > len(transactions) * 0.3:
        warnings.append("نسبة كبيرة من المعاملات بدون وصف بنكي، وقد تفوت بعض الالتزامات.")

    if decision_input and customer.get("salary"):
        installment = decision_input.get("monthly_installment", 0)
        salary = customer["salary"]
        # An installment at or above the whole salary is nonsensical to analyze —
        # a bank rejects the input rather than running numbers on it.
        if installment >= salary:
            blocking.append("القسط المدخل يساوي الراتب الشهري أو يتجاوزه، وهذا غير واقعي للتحليل.")
        elif installment > salary * 0.6:
            warnings.append("القسط المقترح يتجاوز 60% من الراتب الشهري قبل احتساب أي التزامات أخرى.")

    return {
        "is_valid": not blocking,
        "warnings_ar": warnings,
        "blocking_errors_ar": blocking,
    }
