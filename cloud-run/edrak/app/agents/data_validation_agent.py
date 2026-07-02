def validate_data(customer, transactions, loans, profile, decision_input):
    warnings = []

    if not customer:
        warnings.append("لم يتم العثور على بيانات العميل.")
    elif not customer.get("salary"):
        warnings.append("راتب العميل غير متوفر.")

    if not transactions:
        warnings.append("لا توجد معاملات كافية لتحليل سلوك الإنفاق.")

    if loans is None:
        warnings.append("تعذر قراءة بيانات القروض.")

    if not profile:
        warnings.append("لم يتم بناء الملف المالي المشتق.")

    if decision_input.get("monthly_installment", 0) <= 0:
        warnings.append("القسط الشهري المتوقع يجب أن يكون أكبر من صفر.")

    if decision_input.get("duration_months", 0) <= 0:
        warnings.append("مدة الالتزام يجب أن تكون أكبر من صفر.")

    confidence = "عالية"
    if warnings:
        confidence = "متوسطة" if customer and profile else "منخفضة"

    return {
        "is_valid": customer is not None
        and profile is not None
        and decision_input.get("monthly_installment", 0) > 0
        and decision_input.get("duration_months", 0) > 0,
        "warnings_ar": warnings,
        "confidence": confidence,
    }
