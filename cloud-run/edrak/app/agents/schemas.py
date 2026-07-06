from typing import Literal

from pydantic import BaseModel, Field


Confidence = Literal["عالية", "متوسطة", "منخفضة"]
RiskLevel = Literal["منخفض", "متوسط", "مرتفع", "حرج"]
Recommendation = Literal["المضي قدمًا", "الحذر", "التأجيل", "التجنّب"]


class CustomerData(BaseModel):
    customer_id: str
    ar_name: str
    en_name: str
    username_en: str | None = None
    salary: float
    current_balance: float | None = None


class TransactionData(BaseModel):
    transaction_id: str
    customer_id: str
    transaction_date: str
    merchant: str
    category: str
    amount: float
    transaction_type: str
    is_recurring: bool = False


class LoanData(BaseModel):
    loan_id: str
    customer_id: str
    loan_type: str
    loan_total_amount: float
    total_profit_amount: float
    total_amount: float
    remaining_amount: float
    monthly_installment: float
    status: str


class UserProfileData(BaseModel):
    customer_id: str
    ar_name: str
    en_name: str
    salary: float
    current_balance: float
    active_loans_count: int
    total_remaining_loans: float
    monthly_loan_installments: float
    avg_monthly_spending: float
    avg_flexible_spending: float
    recurring_obligations: float
    savings_estimate: float
    obligation_ratio: float
    spending_behavior_summary_ar: str
    risk_preference_estimate_ar: str
    profile_generated_at: str | None = None


class DecisionInputData(BaseModel):
    customer_id: str
    goal_type: str
    goal_amount: float
    monthly_installment: float
    duration_months: int
    down_payment: float = 0
    urgency: str


class ToolOutputs(BaseModel):
    obligation_ratio_before: float
    obligation_ratio_after: float
    monthly_buffer_after: float
    risk_score: int = Field(ge=0, le=100)
    safety_score: int = Field(ge=0, le=100)
    recurring_obligations: float
    monthly_loan_installments: float
    avg_flexible_spending: float
    deterministic_recommendation: Recommendation


class DataValidationOutput(BaseModel):
    is_valid: bool
    confidence: Confidence
    warnings_ar: list[str] = []
    blocking_errors_ar: list[str] = []
    trace_message_ar: str


class ProfileAgentOutput(BaseModel):
    profile_summary_ar: str
    income_status_ar: str
    savings_status_ar: str
    obligations_status_ar: str
    spending_behavior_ar: str
    profile_concerns_ar: list[str] = []
    trace_message_ar: str


class RiskAgentOutput(BaseModel):
    risk_summary_ar: str
    risk_factors_ar: list[str] = []
    financial_seatbelt_status: str
    risk_level_ar: RiskLevel
    trace_message_ar: str


class AlternativesAgentOutput(BaseModel):
    safer_options_ar: list[str] = []
    readiness_path_ar: dict[str, list[str]]
    trace_message_ar: str


class RecommendationAgentOutput(BaseModel):
    recommendation: Recommendation
    summary_ar: str
    explanation_ar: str
    trace_message_ar: str


class AgentContext(BaseModel):
    customer: CustomerData
    transactions: list[TransactionData]
    loans: list[LoanData]
    user_profile: UserProfileData
    decision_input: DecisionInputData
    tool_outputs: ToolOutputs
    validation: DataValidationOutput | None = None
    profile_analysis: ProfileAgentOutput | None = None
    risk_analysis: RiskAgentOutput | None = None
    alternatives: AlternativesAgentOutput | None = None
    recommendation: RecommendationAgentOutput | None = None
    agent_trace_ar: list[dict] = []
