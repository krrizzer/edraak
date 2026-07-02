def analyze_profile(profile):
    obligation_ratio = round((profile["monthly_obligations"] / profile["monthly_income"]) * 100)
    savings_months = round(profile["savings"] / max(profile["monthly_obligations"], 1), 1)

    if obligation_ratio < 30:
        obligation_status = "منخفضة"
    elif obligation_ratio < 50:
        obligation_status = "متوسطة"
    else:
        obligation_status = "مرتفعة"

    if savings_months >= 6:
        savings_status = "قوية"
    elif savings_months >= 3:
        savings_status = "مقبولة"
    else:
        savings_status = "محدودة"

    return {
        "summary": profile["behavior_summary_ar"],
        "obligation_status": obligation_status,
        "savings_status": savings_status,
        "message_ar": (
            f"نسبة الالتزامات الحالية {obligation_ratio}%، "
            f"والمدخرات تغطي نحو {savings_months} شهر من الالتزامات."
        ),
    }
