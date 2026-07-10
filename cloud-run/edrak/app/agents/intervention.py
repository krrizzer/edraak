"""Intervention Agent: writes ONE short actionable Arabic alert for the Financial Radar."""
import logging

from app.agents.gemini_client import audit_numbers, run_gemini_agent
from app.agents.schemas import InterventionOutput


logger = logging.getLogger("edraak.agents.intervention")

INSTRUCTION = """
You are the Edraak Intervention Agent.
The radar engine detected that the customer's current spending pace will leave
them short before a committed payment this month. Write ONE short alert.
Do:
- One paragraph, direct and respectful, like a helpful friend — not a report
  and not a lecture.
- Say what will happen, when, the exact gap amount, and the single most
  effective fix based on cause_category (for example: reducing this week's cafe
  spending covers the gap).
- Use only numbers present in the input payload.
- title_ar is a few words, e.g. "تنبيه: قسط يوم ٢٧ في خطر".
- If has_gap is false, write a short reassurance that the month is on track,
  citing the projected end-of-month balance.
- You Must Answer in Arabic. 
Do not:
- Do not invent numbers, dates, or causes.
- Do not shame the customer.
- Do not suggest borrowing to cover the gap.
"""


def intervene(payload: dict) -> InterventionOutput:
    """Run the intervention agent over the radar detection output."""
    output = run_gemini_agent("intervention", payload, InterventionOutput, INSTRUCTION)
    audit_numbers("intervention", [output.title_ar, output.message_ar], payload)
    logger.info("flow.agent.intervention.completed has_gap=%s message=Alert text ready",
                payload.get("has_gap"))
    return output
