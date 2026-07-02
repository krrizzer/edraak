def generate_final_explanation(recommendation, profile, decision_input, metrics):
    goal_amount = decision_input.get("goal_amount", 0)
    installment = decision_input.get("monthly_installment", 0)

    return (
        f"التوصية هي {recommendation} لأن الالتزامات سترتفع من "
        f"{metrics['obligation_ratio_before']}% إلى {metrics['obligation_ratio_after']}% "
        f"بعد إضافة قسط شهري قدره {installment:,} ريال لهدف قيمته {goal_amount:,} ريال. "
        f"الفائض المتوقع بعد القرار هو {metrics['monthly_buffer_after']:,} ريال، "
        f"ودرجة المخاطر {metrics['risk_score']} من 100 مقابل درجة أمان {metrics['safety_score']} من 100."
    )
