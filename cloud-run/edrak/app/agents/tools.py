from app.functions.tools import (
    calculate_monthly_buffer,
    calculate_obligation_ratio,
    calculate_risk_score,
)


# These wrappers stay small so they can become Google ADK tools later.
def obligation_ratio_tool(monthly_obligations, salary):
    return calculate_obligation_ratio(monthly_obligations, salary)


def monthly_buffer_tool(salary, monthly_obligations, new_installment, avg_flexible_spending):
    return calculate_monthly_buffer(
        salary,
        monthly_obligations,
        new_installment,
        avg_flexible_spending,
    )


def risk_score_tool(profile, decision_input, metrics):
    return calculate_risk_score(profile, decision_input, metrics)
