def calculate_obligation_ratio(monthly_obligations, monthly_income):
    if monthly_income <= 0:
        return 100
    return round((monthly_obligations / monthly_income) * 100)


def calculate_monthly_buffer(monthly_income, monthly_obligations, monthly_installment, avg_flexible_spending):
    return round(monthly_income - monthly_obligations - monthly_installment - avg_flexible_spending)


def calculate_risk_score(profile, decision_input, metrics):
    score = 20

    obligation_after = metrics["obligation_ratio_after"]
    buffer_after = metrics["monthly_buffer_after"]
    installment = decision_input.get("monthly_installment", 0)
    income = profile.get("monthly_income", 1)
    savings = profile.get("savings", 0)
    goal_amount = decision_input.get("goal_amount", 0)
    urgency = decision_input.get("urgency", "medium")

    if obligation_after >= 65:
        score += 35
    elif obligation_after >= 50:
        score += 25
    elif obligation_after >= 35:
        score += 12

    if buffer_after < 0:
        score += 35
    elif buffer_after < income * 0.08:
        score += 22
    elif buffer_after < income * 0.15:
        score += 10

    if installment > income * 0.2:
        score += 12

    if savings < goal_amount * 0.1:
        score += 10

    if urgency == "high":
        score += 8
    elif urgency == "low":
        score -= 5

    if profile.get("avg_flexible_spending", 0) > income * 0.25:
        score += 8

    return max(0, min(100, round(score)))


def generate_recommendation(risk_score, obligation_ratio_after, monthly_buffer_after):
    if risk_score >= 85 or monthly_buffer_after < 0:
        return "التجنّب"
    if risk_score >= 65 or obligation_ratio_after >= 55:
        return "التأجيل"
    if risk_score >= 40 or obligation_ratio_after >= 40:
        return "الحذر"
    return "المضي قدمًا"


def generate_safer_options(profile, decision_input, metrics):
    installment = decision_input.get("monthly_installment", 0)
    goal_amount = decision_input.get("goal_amount", 0)
    down_payment = decision_input.get("down_payment", 0)
    flexible = profile.get("avg_flexible_spending", 0)

    options = [
        f"خفض مبلغ الهدف إلى نحو {round(goal_amount * 0.85):,} ريال لتخفيف الالتزام الشهري.",
        f"رفع الدفعة المقدمة من {down_payment:,} ريال لتقليل القسط أو مدة الالتزام.",
        f"استهداف قسط شهري لا يتجاوز {round(installment * 0.75):,} ريال قبل توقيع الالتزام.",
    ]

    if flexible > profile.get("monthly_income", 0) * 0.2:
        options.append(f"خفض الإنفاق المرن بنحو {round(flexible * 0.2):,} ريال شهريا لمدة 90 يوما.")

    if metrics["monthly_buffer_after"] < profile.get("monthly_income", 0) * 0.1:
        options.append("بناء احتياطي طوارئ يغطي ثلاثة أشهر من الالتزامات قبل القرار.")

    options.append("تأجيل القرار شهرين ومراجعة النسبة بعد تحسين الفائض الشهري.")
    return options


def generate_readiness_path(profile, decision_input, metrics):
    target_buffer = max(round(profile["monthly_income"] * 0.15), decision_input.get("monthly_installment", 0))
    flexible_cut = max(round(profile["avg_flexible_spending"] * 0.15), 500)

    return {
        "30_days": [
            f"تجميد المصروفات غير الضرورية وخفض الإنفاق المرن بنحو {flexible_cut:,} ريال.",
            "مراجعة كل الالتزامات القائمة وتحديد ما يمكن سداده أو إعادة جدولته.",
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
