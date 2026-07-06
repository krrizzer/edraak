from app.agents.gemini_client import GeminiAgentError, run_gemini_agent
from app.agents.schemas import RecommendationAgentOutput


INSTRUCTION = """
You are the Edraak Final Recommendation Agent.
Do:
- Write the final recommendation in clear Arabic.
- Set recommendation exactly equal to tool_outputs.deterministic_recommendation.
- Explain the decision using the already-calculated risk_score, safety_score, obligation ratios, and monthly buffer.
- Use outputs from validation, profile, risk, and alternatives agents when present in context.
- Use Arabic for every user-facing field.
Do not:
- Do not override tool_outputs.deterministic_recommendation.
- Do not invent numbers, loans, transactions, balances, or customer profile details.
- Do not use decision_requests or recommendations as analytical input; those tables are storage-only.
- Do not return Markdown.
"""


def choose_recommendation(risk_score, obligation_ratio_after, monthly_buffer_after):
    if monthly_buffer_after < 0:
        return "التجنّب"
    if obligation_ratio_after >= 60 or risk_score >= 80:
        return "التجنّب"
    if obligation_ratio_after >= 45 or risk_score >= 65:
        return "التأجيل"
    if obligation_ratio_after >= 35 or risk_score >= 45:
        return "الحذر"
    return "المضي قدمًا"


def generate_recommendation(context):
    output = run_gemini_agent(
        "recommendation_agent",
        context,
        RecommendationAgentOutput,
        INSTRUCTION,
    )
    expected = context.tool_outputs.deterministic_recommendation
    if output.recommendation != expected:
        raise GeminiAgentError(
            f"Recommendation agent returned {output.recommendation!r}, expected {expected!r}."
        )
    return output
