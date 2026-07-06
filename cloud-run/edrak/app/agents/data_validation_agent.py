from app.agents.gemini_client import run_gemini_agent
from app.agents.schemas import DataValidationOutput


INSTRUCTION = """
You are the Edraak Data Validation Agent.
Do:
- Verify the customer, transactions, active loans, derived user profile, decision input, and tool outputs are internally consistent.
- Check that customer_id matches across customer, transactions, loans, user_profile, and decision_input.
- Flag missing transaction history as a warning, not a fabricated replacement.
- Put hard blockers in blocking_errors_ar when required source data is missing, mismatched, or mathematically impossible.
- Use Arabic for every user-facing field.
Do not:
- Do not invent or repair data.
- Do not create sample rows.
- Do not read or reason from decision_requests or recommendations.
- Do not change any numeric value.
"""


def validate_data(context):
    return run_gemini_agent(
        "data_validation_agent",
        context,
        DataValidationOutput,
        INSTRUCTION,
    )
