def generate_alternatives(profile, decision_input, metrics):
    goal_amount = decision_input.get("goal_amount", 0)
    installment = decision_input.get("monthly_installment", 0)
    down_payment = decision_input.get("down_payment", 0)
    flexible = profile.get("avg_flexible_spending", 0)

    options = [
        f"خفض مبلغ الهدف إلى نحو {round(goal_amount * 0.85):,} ريال لتقليل الالتزام الشهري.",
        f"رفع الدفعة المقدمة من {down_payment:,} ريال لتقليل مبلغ التمويل.",
        f"استهداف قسط شهري لا يتجاوز {round(installment * 0.75):,} ريال قبل توقيع الالتزام.",
        "تأجيل القرار 60 إلى 90 يوما وإعادة التحليل بعد تحسين الفائض الشهري.",
    ]

    if flexible > profile["salary"] * 0.2:
        options.append(
            f"خفض الإنفاق المرن بنحو {round(flexible * 0.2):,} ريال شهريا لمدة 90 يوما."
        )

    if metrics["monthly_buffer_after"] < profile["salary"] * 0.1:
        options.append("بناء احتياطي طوارئ يغطي ثلاثة أشهر من الالتزامات قبل القرار.")

    if profile["active_loans_count"] > 0:
        options.append("مراجعة القروض الحالية وإعادة هيكلة الالتزامات إذا أمكن قبل إضافة التزام جديد.")

    return options
