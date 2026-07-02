import os

from app.agents.alternatives_agent import generate_alternatives
from app.agents.profile_agent import analyze_profile
from app.agents.recommendation_agent import generate_final_explanation
from app.agents.risk_agent import analyze_risk
from app.agents.tools import (
    monthly_buffer_tool,
    obligation_ratio_tool,
    readiness_path_tool,
    recommendation_tool,
    risk_score_tool,
)

try:
    from google.adk.agents import Agent  # type: ignore
except Exception:
    Agent = None


def run_edraak_agent(profile, transactions, decision_input):
    """Mock root orchestrator. Replace this function body with ADK orchestration later."""
    use_adk = os.getenv("USE_ADK", "false").lower() == "true"
    use_gemini = os.getenv("USE_GEMINI", "false").lower() == "true"

    if use_adk and Agent is not None and use_gemini:
        # Future path:
        # 1. Create an ADK root agent.
        # 2. Register tools from app.agents.tools.
        # 3. Delegate profile, risk, alternatives, and recommendation tasks.
        pass

    profile_summary = analyze_profile(profile)

    obligation_ratio_before = obligation_ratio_tool(
        profile["monthly_obligations"],
        profile["monthly_income"],
    )
    obligation_ratio_after = obligation_ratio_tool(
        profile["monthly_obligations"] + decision_input["monthly_installment"],
        profile["monthly_income"],
    )
    monthly_buffer_after = monthly_buffer_tool(
        profile["monthly_income"],
        profile["monthly_obligations"],
        decision_input["monthly_installment"],
        profile["avg_flexible_spending"],
    )

    metrics = {
        "obligation_ratio_before": obligation_ratio_before,
        "obligation_ratio_after": obligation_ratio_after,
        "monthly_buffer_after": monthly_buffer_after,
        "transaction_count": len(transactions),
    }
    risk_score = risk_score_tool(profile, decision_input, metrics)
    metrics["risk_score"] = risk_score
    metrics["safety_score"] = 100 - risk_score

    recommendation = recommendation_tool(
        risk_score,
        obligation_ratio_after,
        monthly_buffer_after,
    )
    risk_factors = analyze_risk(profile, decision_input, metrics)
    safer_options = generate_alternatives(profile, decision_input, metrics)
    readiness_path = readiness_path_tool(profile, decision_input, metrics)
    explanation = generate_final_explanation(recommendation, profile, decision_input, metrics)

    return {
        "recommendation": recommendation,
        "risk_score": risk_score,
        "safety_score": metrics["safety_score"],
        "obligation_ratio_before": obligation_ratio_before,
        "obligation_ratio_after": obligation_ratio_after,
        "monthly_buffer_after": monthly_buffer_after,
        "financial_seatbelt_status": "مفعّل",
        "explanation_ar": explanation,
        "risk_factors_ar": risk_factors,
        "safer_options_ar": safer_options,
        "readiness_path_ar": readiness_path,
        "agent_trace_ar": [
            {
                "agent": "وكيل الملف المالي",
                "status": "اكتمل",
                "message": profile_summary["message_ar"],
            },
            {
                "agent": "وكيل مخاطر الالتزامات",
                "status": "اكتمل",
                "message": f"تم حساب درجة المخاطر عند {risk_score} من 100.",
            },
            {
                "agent": "وكيل البدائل",
                "status": "اكتمل",
                "message": f"تم توليد {len(safer_options)} بدائل أكثر أمانا.",
            },
            {
                "agent": "وكيل التوصية",
                "status": "اكتمل",
                "message": f"التوصية النهائية: {recommendation}.",
            },
        ],
    }
