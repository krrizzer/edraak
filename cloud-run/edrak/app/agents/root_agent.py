import logging

from app.agents.alternatives_agent import generate_alternatives
from app.agents.data_validation_agent import validate_data
from app.agents.profile_agent import analyze_profile
from app.agents.recommendation_agent import choose_recommendation, generate_recommendation
from app.agents.risk_agent import analyze_risk
from app.agents.schemas import (
    AgentContext,
    CustomerData,
    DecisionInputData,
    LoanData,
    ToolOutputs,
    TransactionData,
    UserProfileData,
)
from app.agents.tools import monthly_buffer_tool, obligation_ratio_tool, risk_score_tool


logger = logging.getLogger("edraak.agents")

AGENT_NAMES = {
    "validation": "وكيل التحقق من البيانات",
    "profile": "وكيل تحليل الملف المالي",
    "risk": "وكيل تحليل المخاطر",
    "alternatives": "وكيل البدائل",
    "recommendation": "وكيل التوصية",
}


def run_edraak_agent(customer, transactions, loans, user_profile, decision_input):
    customer_id = customer.get("customer_id")
    logger.info(
        "flow.agents.start customer_id=%s goal_type=%s message=Agent workflow started after BigQuery data collection",
        customer_id,
        decision_input.get("goal_type"),
    )

    logger.info("flow.tools.start customer_id=%s message=Running deterministic financial tools before Gemini agents", customer_id)
    tool_outputs = _run_tools(user_profile, decision_input)
    logger.info(
        "flow.tools.completed customer_id=%s before=%s after=%s buffer=%s risk=%s safety=%s recommendation=%s message=Financial calculations finished",
        customer_id,
        tool_outputs["obligation_ratio_before"],
        tool_outputs["obligation_ratio_after"],
        tool_outputs["monthly_buffer_after"],
        tool_outputs["risk_score"],
        tool_outputs["safety_score"],
        tool_outputs["deterministic_recommendation"],
    )

    context = AgentContext(
        customer=CustomerData.model_validate(customer),
        transactions=[TransactionData.model_validate(_stringify_dates(item)) for item in transactions],
        loans=[LoanData.model_validate(_stringify_dates(item)) for item in loans],
        user_profile=UserProfileData.model_validate(_stringify_dates(user_profile)),
        decision_input=DecisionInputData.model_validate(decision_input),
        tool_outputs=ToolOutputs.model_validate(tool_outputs),
    )
    logger.info(
        "flow.agents.context_ready customer_id=%s transactions=%s loans=%s active_loans=%s message=Strict agent context built from collected data",
        customer_id,
        len(context.transactions),
        len(context.loans),
        context.user_profile.active_loans_count,
    )

    logger.info("flow.agent.validation.start customer_id=%s message=Data validation agent is checking source consistency", customer_id)
    validation = validate_data(context)
    context.validation = validation
    _append_trace(context, "validation", validation.trace_message_ar)
    logger.info(
        "flow.agent.validation.completed valid=%s confidence=%s warnings=%s blocking_errors=%s message=Data validation agent finished",
        validation.is_valid,
        validation.confidence,
        len(validation.warnings_ar),
        len(validation.blocking_errors_ar),
    )
    if not validation.is_valid:
        logger.warning("flow.agents.failed customer_id=%s reason=validation_failed message=Agent workflow stopped because validation failed", customer_id)
        raise ValueError("; ".join(validation.blocking_errors_ar) or "Data validation failed.")

    logger.info("flow.agent.profile.start customer_id=%s message=Profile agent is explaining the derived user profile", customer_id)
    profile_analysis = analyze_profile(context)
    context.profile_analysis = profile_analysis
    _append_trace(context, "profile", profile_analysis.trace_message_ar)
    logger.info("flow.agent.profile.completed concerns=%s message=Profile agent finished", len(profile_analysis.profile_concerns_ar))

    logger.info("flow.agent.risk.start customer_id=%s message=Risk agent is analyzing the new commitment impact", customer_id)
    risk_analysis = analyze_risk(context)
    context.risk_analysis = risk_analysis
    _append_trace(context, "risk", risk_analysis.trace_message_ar)
    logger.info("flow.agent.risk.completed risk_level=%s factors=%s message=Risk agent finished", risk_analysis.risk_level_ar, len(risk_analysis.risk_factors_ar))

    logger.info("flow.agent.alternatives.start customer_id=%s message=Alternatives agent is preparing safer options and readiness path", customer_id)
    alternatives = generate_alternatives(context)
    context.alternatives = alternatives
    _append_trace(context, "alternatives", alternatives.trace_message_ar)
    logger.info("flow.agent.alternatives.completed options=%s message=Alternatives agent finished", len(alternatives.safer_options_ar))

    logger.info("flow.agent.recommendation.start customer_id=%s message=Recommendation agent is writing the final explanation", customer_id)
    recommendation = generate_recommendation(context)
    context.recommendation = recommendation
    _append_trace(context, "recommendation", recommendation.trace_message_ar)
    logger.info("flow.agent.recommendation.completed recommendation=%s message=Recommendation agent finished", recommendation.recommendation)

    logger.info("flow.agents.completed customer_id=%s recommendation=%s message=Agent workflow completed", customer_id, recommendation.recommendation)
    return _final_response(context)


def _run_tools(profile, decision_input):
    recurring_obligations = profile["recurring_obligations"]
    monthly_loan_installments = profile["monthly_loan_installments"]
    base_obligations = recurring_obligations + monthly_loan_installments

    obligation_before = obligation_ratio_tool(base_obligations, profile["salary"])
    obligation_after = obligation_ratio_tool(
        base_obligations + decision_input["monthly_installment"],
        profile["salary"],
    )
    monthly_buffer_after = monthly_buffer_tool(
        profile["salary"],
        recurring_obligations,
        monthly_loan_installments,
        profile["avg_flexible_spending"],
        decision_input["monthly_installment"],
    )

    metrics = {
        "obligation_ratio_before": obligation_before,
        "obligation_ratio_after": obligation_after,
        "monthly_buffer_after": monthly_buffer_after,
    }
    risk_score = risk_score_tool(profile, decision_input, metrics)
    safety_score = max(0, min(100, 100 - risk_score))

    return {
        "obligation_ratio_before": obligation_before,
        "obligation_ratio_after": obligation_after,
        "monthly_buffer_after": monthly_buffer_after,
        "risk_score": risk_score,
        "safety_score": safety_score,
        "recurring_obligations": recurring_obligations,
        "monthly_loan_installments": monthly_loan_installments,
        "avg_flexible_spending": profile["avg_flexible_spending"],
        "deterministic_recommendation": choose_recommendation(
            risk_score,
            obligation_after,
            monthly_buffer_after,
        ),
    }


def _append_trace(context, agent_key, message):
    context.agent_trace_ar.append(
        {
            "agent": AGENT_NAMES[agent_key],
            "status": "اكتمل",
            "message": message,
        }
    )


def _final_response(context):
    tools = context.tool_outputs
    profile = context.user_profile
    validation = context.validation
    profile_analysis = context.profile_analysis
    risk_analysis = context.risk_analysis
    alternatives = context.alternatives
    recommendation = context.recommendation

    return {
        "customer": _customer_response(context),
        "generated_profile": _profile_response(profile),
        "recommendation": recommendation.recommendation,
        "risk_score": tools.risk_score,
        "safety_score": tools.safety_score,
        "obligation_ratio_before": tools.obligation_ratio_before,
        "obligation_ratio_after": tools.obligation_ratio_after,
        "monthly_buffer_after": tools.monthly_buffer_after,
        "financial_seatbelt_status": risk_analysis.financial_seatbelt_status,
        "confidence": validation.confidence,
        "validation_warnings_ar": validation.warnings_ar,
        "profile_summary_ar": profile_analysis.profile_summary_ar,
        "explanation_ar": recommendation.explanation_ar,
        "risk_factors_ar": risk_analysis.risk_factors_ar,
        "safer_options_ar": alternatives.safer_options_ar,
        "readiness_path_ar": alternatives.readiness_path_ar,
        "agent_trace_ar": context.agent_trace_ar,
    }


def _customer_response(context):
    return {
        "customer_id": context.customer.customer_id,
        "ar_name": context.customer.ar_name,
        "en_name": context.customer.en_name,
    }


def _profile_response(profile):
    return {
        "customer_id": profile.customer_id,
        "salary": profile.salary,
        "current_balance": profile.current_balance,
        "active_loans_count": profile.active_loans_count,
        "total_remaining_loans": profile.total_remaining_loans,
        "monthly_loan_installments": profile.monthly_loan_installments,
        "avg_monthly_spending": profile.avg_monthly_spending,
        "avg_flexible_spending": profile.avg_flexible_spending,
        "recurring_obligations": profile.recurring_obligations,
        "savings_estimate": profile.savings_estimate,
        "obligation_ratio": profile.obligation_ratio,
        "spending_behavior_summary_ar": profile.spending_behavior_summary_ar,
    }


def _stringify_dates(payload):
    return {
        key: value.isoformat() if hasattr(value, "isoformat") else value
        for key, value in payload.items()
    }
