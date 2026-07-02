def analyze_profile(profile):
    obligation_ratio = profile["obligation_ratio"]
    savings_months = round(
        profile["savings_estimate"] / max(profile["recurring_obligations"], 1),
        1,
    )

    if profile["salary"] >= 20000:
        income_status = "قوي"
    elif profile["salary"] >= 14000:
        income_status = "متوسط"
    else:
        income_status = "محدود"

    if savings_months >= 6:
        savings_status = "قوية"
    elif savings_months >= 3:
        savings_status = "مقبولة"
    else:
        savings_status = "محدودة"

    if obligation_ratio >= 55:
        obligations_status = "مرتفعة"
    elif obligation_ratio >= 35:
        obligations_status = "متوسطة"
    else:
        obligations_status = "منخفضة"

    return {
        "income_status": income_status,
        "savings_status": savings_status,
        "obligations_status": obligations_status,
        "message_ar": (
            f"تم بناء الملف المالي من بيانات البنك. الدخل {income_status}، "
            f"المدخرات {savings_status}، ونسبة الالتزامات الحالية {obligation_ratio}%."
        ),
    }
