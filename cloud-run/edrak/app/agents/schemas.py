"""Strict Pydantic response schemas for every Gemini agent call."""
from typing import Literal

from pydantic import BaseModel, Field


# Modern, natural Arabic verdict labels (badge + advisor echo + UI).
Recommendation = Literal["قرار آمن", "مقبول بحذر", "الأفضل تأجيله", "غير مناسب"]

ObligationType = Literal[
    "bnpl_installment",
    "jamiya",
    "family_support",
    "rent",
    "subscription",
    "salary",
    "loan_installment_other_bank",
    "flexible_spending",
    "one_off",
]

TransactionCategory = Literal[
    "cafes",
    "restaurants",
    "groceries",
    "shopping",
    "entertainment",
    "fuel",
    "transport",
    "housing",
    "bills",
    "healthcare",
    "transfers",
    "other",
]


class GroupLabel(BaseModel):
    """The agent's classification of ONE deterministically-detected recurring group.

    The agent never sets amounts, days, or banks — Python owns those from the
    grouped transactions. The agent only decides what the group means.
    """
    group_id: str
    obligation_type: ObligationType
    counterparty: str
    label_ar: str
    is_committed: bool
    # remaining_months only when the descriptions imply a countdown ("2 of 4").
    remaining_months: int | None = None
    confidence: float = Field(ge=0, le=1)


class TransactionIntelligenceOutput(BaseModel):
    labels: list[GroupLabel] = []
    trace_message_ar: str


class TransactionPatternLabel(BaseModel):
    """AI meaning assigned to one merchant/description pattern."""
    pattern_id: str
    category: TransactionCategory
    confidence: float = Field(ge=0, le=1)


class TransactionCategorizationOutput(BaseModel):
    labels: list[TransactionPatternLabel] = []
    trace_message_ar: str


class DecisionAdvisorOutput(BaseModel):
    """The Arabic result the user reads. recommendation must echo the deterministic verdict."""
    recommendation: Recommendation
    explanation_ar: str
    risk_factors_ar: list[str] = []
    safer_options_ar: list[str] = []
    trace_message_ar: str


class InterventionOutput(BaseModel):
    """Number-free human guidance appended to deterministic radar facts."""
    guidance_ar: str
    trace_message_ar: str


class SufficiencyOutput(BaseModel):
    """The LLM's judgment on whether the linked data forms a complete financial picture."""
    looks_complete: bool
    confidence: float = Field(ge=0, le=1)
    findings_ar: list[str] = []
    trace_message_ar: str
