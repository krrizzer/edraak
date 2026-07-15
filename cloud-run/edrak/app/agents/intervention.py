"""Intervention Agent: adds number-free guidance to deterministic radar facts."""
import logging

from app.agents.gemini_client import audit_numbers, run_gemini_agent
from app.agents.schemas import InterventionOutput


logger = logging.getLogger("edraak.agents.intervention")

INSTRUCTION = """
You are the Edraak Intervention Agent. Deterministic code will render every
amount, date, percentage, and equation. Your job is only to add human guidance.

Return:
- guidance_ar: one short, direct Arabic sentence with the best action, based on
  cause_category and suggested_cuts when present.
- trace_message_ar: a short Arabic explanation of your wording step.

Hard rules:
- Do not write digits, number words, amounts, dates, percentages, equations, or
  computed claims in guidance_ar. The application owns all facts.
- Do not invent a cause. If evidence is weak, give general spending guidance.
- Do not shame the customer or suggest borrowing.
- Do not suggest using savings except as a last resort.
- Answer in Arabic.
"""


def intervene(payload: dict) -> InterventionOutput:
    """Run the intervention agent over the radar detection output."""
    output = run_gemini_agent("intervention", payload, InterventionOutput, INSTRUCTION)
    audit_numbers("intervention", [output.guidance_ar], payload)
    logger.info("flow.agent.intervention.completed has_gap=%s message=Alert guidance ready",
                payload.get("has_gap"))
    return output
