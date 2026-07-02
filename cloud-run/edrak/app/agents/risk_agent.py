def analyze_risk(profile, loans, decision_input, metrics):
    factors = []

    if profile["active_loans_count"] > 0:
        factors.append(
            f"لدى العميل {profile['active_loans_count']} قروض نشطة بإجمالي متبقٍ {profile['total_remaining_loans']:,} ريال."
        )

    if metrics["obligation_ratio_after"] >= 55:
        factors.append(
            f"نسبة الالتزامات بعد القرار سترتفع إلى {metrics['obligation_ratio_after']}% من الراتب."
        )
    elif metrics["obligation_ratio_after"] >= 40:
        factors.append(
            f"نسبة الالتزامات بعد القرار تصبح {metrics['obligation_ratio_after']}% وتحتاج متابعة."
        )

    if metrics["monthly_buffer_after"] < 0:
        factors.append(
            f"الفائض الشهري المتوقع بعد القرار يصبح سالبا: {metrics['monthly_buffer_after']:,} ريال."
        )
    elif metrics["monthly_buffer_after"] < profile["salary"] * 0.1:
        factors.append(
            f"الفائض الشهري المتوقع منخفض: {metrics['monthly_buffer_after']:,} ريال."
        )

    if profile["avg_flexible_spending"] > profile["salary"] * 0.25:
        factors.append(
            f"الإنفاق المرن مرتفع ويبلغ حوالي {profile['avg_flexible_spending']:,} ريال شهريا."
        )

    if decision_input.get("urgency") == "high":
        factors.append("درجة الاستعجال عالية وقد تؤدي إلى قرار أقل جودة.")

    if not factors:
        factors.append("المؤشرات الأساسية لا تظهر ضغطا ماليا عاليا بعد القرار.")

    return factors
