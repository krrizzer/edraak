from app.functions.financial_tools import (
    calculate_monthly_buffer,
    calculate_obligation_ratio,
    calculate_risk_score,
    generate_readiness_path,
    generate_recommendation,
    generate_safer_options,
)


# These wrappers are intentionally small. Later, each can become a Google ADK tool.
def obligation_ratio_tool(monthly_obligations, monthly_income):
    return calculate_obligation_ratio(monthly_obligations, monthly_income)


def monthly_buffer_tool(monthly_income, monthly_obligations, monthly_installment, avg_flexible_spending):
    return calculate_monthly_buffer(
        monthly_income,
        monthly_obligations,
        monthly_installment,
        avg_flexible_spending,
    )


def risk_score_tool(profile, decision_input, metrics):
    return calculate_risk_score(profile, decision_input, metrics)


def recommendation_tool(risk_score, obligation_ratio_after, monthly_buffer_after):
    return generate_recommendation(risk_score, obligation_ratio_after, monthly_buffer_after)


def safer_options_tool(profile, decision_input, metrics):
    return generate_safer_options(profile, decision_input, metrics)


def readiness_path_tool(profile, decision_input, metrics):
    return generate_readiness_path(profile, decision_input, metrics)
