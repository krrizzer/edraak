def choose_recommendation(risk_score, obligation_ratio_after, monthly_buffer_after):
    if risk_score >= 85 or monthly_buffer_after < 0:
        return "التجنّب"
    if risk_score >= 65 or obligation_ratio_after >= 55:
        return "التأجيل"
    if risk_score >= 40 or obligation_ratio_after >= 40:
        return "الحذر"
    return "المضي قدمًا"


def generate_readiness_path(profile, decision_input, metrics):
    target_buffer = max(round(profile["salary"] * 0.15), decision_input["monthly_installment"])
    flexible_cut = max(round(profile["avg_flexible_spending"] * 0.15), 500)

    return {
        "30_days": [
            f"خفض المصروفات المرنة بنحو {flexible_cut:,} ريال ومراجعة الاشتراكات والمدفوعات المتكررة.",
            "تحديد الالتزامات التي يمكن سدادها أو إعادة جدولتها قبل القرار.",
        ],
        "60_days": [
            f"رفع الفائض الشهري المستهدف إلى {target_buffer:,} ريال قبل إضافة القسط الجديد.",
            "زيادة الدفعة المقدمة أو تقليل مبلغ الهدف بناء على الفائض الفعلي.",
        ],
        "90_days": [
            "إعادة تشغيل التحليل بنفس الأرقام بعد تحسن الفائض والادخار.",
            "المضي فقط إذا انخفضت نسبة الالتزامات وبقي حزام الأمان المالي مفعلا.",
        ],
    }


def generate_final_explanation(recommendation, profile, decision_input, metrics):
    return (
        f"التوصية هي {recommendation}. الراتب الشهري {profile['salary']:,} ريال، "
        f"والالتزامات الحالية تمثل {metrics['obligation_ratio_before']}% من الراتب. "
        f"بعد إضافة قسط شهري جديد قدره {decision_input['monthly_installment']:,} ريال "
        f"ستصل نسبة الالتزامات إلى {metrics['obligation_ratio_after']}%. "
        f"الفائض الشهري المتوقع بعد القرار هو {metrics['monthly_buffer_after']:,} ريال، "
        f"ودرجة المخاطر {metrics['risk_score']} من 100 مقابل درجة أمان {metrics['safety_score']} من 100."
    )
