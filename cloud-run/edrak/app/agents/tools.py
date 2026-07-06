from app.functions.tools import calculate_monthly_buffer, calculate_obligation_ratio, calculate_risk_score


def obligation_ratio_tool(monthly_obligations, salary):
    return calculate_obligation_ratio(monthly_obligations, salary)


def monthly_buffer_tool(
    salary,
    recurring_obligations,
    monthly_loan_installments,
    avg_flexible_spending,
    new_installment,
):
    return calculate_monthly_buffer(
        salary,
        recurring_obligations,
        monthly_loan_installments,
        avg_flexible_spending,
        new_installment,
    )


def risk_score_tool(profile, decision_input, metrics):
    return calculate_risk_score(profile, decision_input, metrics)
