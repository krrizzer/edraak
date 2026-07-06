def calculate_risk_score(profile, decision_input, metrics):
    score = 20
    salary = profile.get("salary", 1)
    savings = profile.get("savings_estimate", 0)
    urgency = decision_input.get("urgency", "medium")

    if metrics["obligation_ratio_after"] >= 65:
        score += 35
    elif metrics["obligation_ratio_after"] >= 55:
        score += 28
    elif metrics["obligation_ratio_after"] >= 45:
        score += 22
    elif metrics["obligation_ratio_after"] >= 35:
        score += 12

    if metrics["monthly_buffer_after"] < 0:
        score += 35
    elif metrics["monthly_buffer_after"] < salary * 0.08:
        score += 22
    elif metrics["monthly_buffer_after"] < salary * 0.15:
        score += 10

    if savings < salary * 0.5:
        score += 10

    if profile.get("active_loans_count", 0) >= 2:
        score += 10
    elif profile.get("active_loans_count", 0) == 1:
        score += 5

    if profile.get("avg_flexible_spending", 0) > salary * 0.25:
        score += 8

    if urgency == "high":
        score += 8
    elif urgency == "low":
        score -= 5

    return max(0, min(100, round(score)))
