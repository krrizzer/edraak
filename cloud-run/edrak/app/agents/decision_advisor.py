"""Decision Advisor Agent: writes the Arabic result the user reads in Mode A.

It never chooses the outcome — the deterministic verdict is passed in and the
response is rejected if the agent tries to change it.
"""
import logging

from app.agents.gemini_client import GeminiAgentError, audit_numbers, run_gemini_agent
from app.agents.schemas import DecisionAdvisorOutput


logger = logging.getLogger("edraak.agents.decision_advisor")

INSTRUCTION = """
You are the Edraak Decision Advisor Agent.
The deterministic engine already simulated the customer's next 12 months across
ALL of their banks and chose the verdict. Your job is to explain it in Arabic.
Do:
- Set recommendation EXACTLY equal to input verdict.verdict. It is not your decision.
- Write explanation_ar grounded in the specific forecast numbers: name the
  shortfall month and amount, the obligations causing it, and which bank they sit at.
- When verdict is "الأفضل تأجيله", build the story around ready_in_months and WHY
  the wait works (for example: the other-bank loan ends in month 2 and the BNPL
  stack ends in month 3), using the forecast events and stress_events causes.
- risk_factors_ar: concrete factors tied to the supplied numbers (BNPL stacking,
  salary timing variance, thin savings cover, peak obligation ratio).
- safer_options_ar: alternatives tied to the customer's real numbers — lower
  installment that keeps the buffer positive, higher down payment, or waiting
  ready_in_months months.
- Keep every number you mention identical to a number in the input payload.
- You act as a professional financial advisor, not a deterministic engine to approve/decline, you just help the customer understand the numbers and the verdict and why it's goood/bad. You explain the numbers and the verdict, but you do not choose it.
Do not:
- Do not change, recompute, or round any number.
- Do not soften or harden the verdict.
- Do not use generic advice that ignores the supplied data.
"""


def advise(payload: dict) -> DecisionAdvisorOutput:
    """Run the advisor and enforce that it echoed the deterministic verdict."""
    expected = payload["verdict"]["verdict"]
    output = run_gemini_agent("decision_advisor", payload, DecisionAdvisorOutput, INSTRUCTION)
    if output.recommendation != expected:
        raise GeminiAgentError(
            f"Decision advisor returned {output.recommendation!r}, expected {expected!r}."
        )
    audit_numbers(
        "decision_advisor",
        [output.explanation_ar, *output.risk_factors_ar, *output.safer_options_ar],
        payload,
    )
    logger.info("flow.agent.decision_advisor.completed recommendation=%s factors=%s options=%s message=Advisor explanation ready",
                output.recommendation, len(output.risk_factors_ar), len(output.safer_options_ar))
    return output
