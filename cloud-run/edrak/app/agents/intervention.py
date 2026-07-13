"""Intervention Agent: writes ONE short actionable Arabic alert for the Financial Radar."""
import logging

from app.agents.gemini_client import audit_numbers, run_gemini_agent
from app.agents.schemas import InterventionOutput


logger = logging.getLogger("edraak.agents.intervention")

INSTRUCTION = """
You are the Edraak Intervention Agent.
The radar engine projected the customer's current month. Write ONE short alert
matching alert_type:
- alert_type == "installment_gap": a committed payment will not be covered.
  Say what will happen, when, the exact gap amount, and the single most
  effective fix based on cause_category (for example: reducing this week's cafe
  spending covers the gap).
- alert_type == "overspend": no payment fails, but the spending pace will drive
  the spendable balance below zero around trajectory.projected_trough.date
  (often before salary day). Say roughly when and by how much, name the
  accelerating categories, and use trajectory.suggested_cuts to propose the
  most effective reductions (each entry says how much cutting that category
  back to its normal pace recovers).
- alert_type == "on_track": write a short reassurance that the month is on
  track, citing the projected end-of-month balance and remaining budget.
Do:
- One paragraph, direct and respectful, like a helpful friend — not a report
  and not a lecture.
- Use only numbers present in the input payload.
- title_ar is a few words, e.g. "تنبيه: قسط يوم ٢٧ في خطر" or "انتبه: صرفك أسرع من ميزانيتك".
- You Must Answer in Arabic.
Do not:
- Do not invent numbers, dates, or causes.
- Do not shame the customer.
- Do not suggest borrowing to cover the gap.
- Do not suggest touching the savings reserve except as a last-resort mention.
"""


def intervene(payload: dict) -> InterventionOutput:
    """Run the intervention agent over the radar detection output."""
    output = run_gemini_agent("intervention", payload, InterventionOutput, INSTRUCTION)
    audit_numbers("intervention", [output.title_ar, output.message_ar], payload)
    logger.info("flow.agent.intervention.completed has_gap=%s message=Alert text ready",
                payload.get("has_gap"))
    return output
