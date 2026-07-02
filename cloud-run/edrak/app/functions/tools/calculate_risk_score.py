def calculate_risk_score(profile, decision_input, metrics):
    score = 20
    salary = profile.get("salary", 1)
    savings = profile.get("savings_estimate", 0)
    urgency = decision_input.get("urgency", "medium")
    installment = decision_input.get("monthly_installment", 0)
    goal_amount = decision_input.get("goal_amount", 0)

    if metrics["obligation_ratio_after"] >= 65:
        score += 35
    elif metrics["obligation_ratio_after"] >= 50:
        score += 25
    elif metrics["obligation_ratio_after"] >= 35:
        score += 12

    if metrics["monthly_buffer_after"] < 0:
        score += 35
    elif metrics["monthly_buffer_after"] < salary * 0.08:
        score += 22
    elif metrics["monthly_buffer_after"] < salary * 0.15:
        score += 10

    if installment > salary * 0.2:
        score += 12

    if savings < goal_amount * 0.1:
        score += 10

    if profile.get("avg_flexible_spending", 0) > salary * 0.25:
        score += 8

    if urgency == "high":
        score += 8
    elif urgency == "low":
        score -= 5

    return max(0, min(100, round(score)))
