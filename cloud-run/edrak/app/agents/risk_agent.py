def analyze_risk(profile, decision_input, metrics):
    factors = []

    if metrics["obligation_ratio_after"] >= 55:
        factors.append(f"نسبة الالتزامات بعد القرار تصل إلى {metrics['obligation_ratio_after']}%.")
    elif metrics["obligation_ratio_after"] >= 40:
        factors.append(f"نسبة الالتزامات بعد القرار تصبح {metrics['obligation_ratio_after']}% وتحتاج مراقبة.")

    if metrics["monthly_buffer_after"] < 0:
        factors.append(f"الفائض الشهري بعد القرار يصبح سالبا: {metrics['monthly_buffer_after']:,} ريال.")
    elif metrics["monthly_buffer_after"] < profile["monthly_income"] * 0.1:
        factors.append(f"الفائض الشهري بعد القرار منخفض: {metrics['monthly_buffer_after']:,} ريال.")

    if decision_input.get("urgency") == "high":
        factors.append("درجة الاستعجال عالية وقد تضغط على جودة القرار.")

    if profile["avg_flexible_spending"] > profile["monthly_income"] * 0.25:
        factors.append("الإنفاق المرن مرتفع مقارنة بالدخل الشهري.")

    if not factors:
        factors.append("المؤشرات الأساسية ضمن نطاق آمن نسبيا مع بقاء المتابعة مهمة.")

    return factors
