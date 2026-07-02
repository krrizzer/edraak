import os

from app.agents.alternatives_agent import generate_alternatives
from app.agents.data_validation_agent import validate_data
from app.agents.profile_agent import analyze_profile
from app.agents.recommendation_agent import (
    choose_recommendation,
    generate_final_explanation,
    generate_readiness_path,
)
from app.agents.risk_agent import analyze_risk
from app.agents.tools import monthly_buffer_tool, obligation_ratio_tool, risk_score_tool


def run_edraak_agent(customer, transactions, loans, profile, decision_input):
    """Runs the current mock agents in sequence. Later, this can become ADK orchestration."""
    use_adk = os.getenv("USE_ADK", "false").lower() == "true"
    use_gemini = os.getenv("USE_GEMINI", "false").lower() == "true"

    if use_adk and use_gemini:
        # Future path:
        # 1. Create an ADK root agent.
        # 2. Register wrappers from app.agents.tools as ADK tools.
        # 3. Run the same validation -> profile -> risk -> alternatives -> recommendation flow.
        pass

    validation = validate_data(customer, transactions, loans, profile, decision_input)
    profile_summary = analyze_profile(profile)

    obligation_before = obligation_ratio_tool(
        profile["recurring_obligations"],
        profile["salary"],
    )
    obligation_after = obligation_ratio_tool(
        profile["recurring_obligations"] + decision_input["monthly_installment"],
        profile["salary"],
    )
    monthly_buffer_after = monthly_buffer_tool(
        profile["salary"],
        profile["recurring_obligations"],
        decision_input["monthly_installment"],
        profile["avg_flexible_spending"],
    )

    metrics = {
        "obligation_ratio_before": obligation_before,
        "obligation_ratio_after": obligation_after,
        "monthly_buffer_after": monthly_buffer_after,
        "transaction_count": len(transactions),
        "active_loans_count": len(loans),
    }
    metrics["risk_score"] = risk_score_tool(profile, decision_input, metrics)
    metrics["safety_score"] = 100 - metrics["risk_score"]

    risk_factors = analyze_risk(profile, loans, decision_input, metrics)
    safer_options = generate_alternatives(profile, decision_input, metrics)
    recommendation = choose_recommendation(
        metrics["risk_score"],
        obligation_after,
        monthly_buffer_after,
    )
    readiness_path = generate_readiness_path(profile, decision_input, metrics)
    explanation = generate_final_explanation(recommendation, profile, decision_input, metrics)

    return {
        "customer": {
            "customer_id": customer["customer_id"],
            "ar_name": customer["ar_name"],
            "en_name": customer["en_name"],
        },
        "generated_profile": {
            "salary": profile["salary"],
            "monthly_loan_installments": profile["monthly_loan_installments"],
            "avg_flexible_spending": profile["avg_flexible_spending"],
            "recurring_obligations": profile["recurring_obligations"],
            "obligation_ratio": profile["obligation_ratio"],
            "active_loans_count": profile["active_loans_count"],
            "total_remaining_loans": profile["total_remaining_loans"],
            "savings_estimate": profile["savings_estimate"],
            "spending_behavior_summary_ar": profile["spending_behavior_summary_ar"],
        },
        "recommendation": recommendation,
        "risk_score": metrics["risk_score"],
        "safety_score": metrics["safety_score"],
        "obligation_ratio_before": obligation_before,
        "obligation_ratio_after": obligation_after,
        "monthly_buffer_after": monthly_buffer_after,
        "financial_seatbelt_status": "مفعّل",
        "confidence": validation["confidence"],
        "validation_warnings_ar": validation["warnings_ar"],
        "explanation_ar": explanation,
        "risk_factors_ar": risk_factors,
        "safer_options_ar": safer_options,
        "readiness_path_ar": readiness_path,
        "agent_trace_ar": [
            {
                "agent": "وكيل التحقق من البيانات",
                "status": "اكتمل",
                "message": "تم التحقق من توفر بيانات العميل والمعاملات والقروض.",
            },
            {
                "agent": "وكيل بناء الملف المالي",
                "status": "اكتمل",
                "message": profile_summary["message_ar"],
            },
            {
                "agent": "وكيل مخاطر الالتزامات",
                "status": "اكتمل",
                "message": "تم تحليل أثر الالتزام الجديد على القروض والفائض الشهري.",
            },
            {
                "agent": "وكيل البدائل",
                "status": "اكتمل",
                "message": f"تم اقتراح {len(safer_options)} بدائل أكثر أمانا.",
            },
            {
                "agent": "وكيل التوصية",
                "status": "اكتمل",
                "message": f"تم إصدار التوصية النهائية: {recommendation}.",
            },
        ],
    }
