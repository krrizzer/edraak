"""Data Sufficiency Agent: judges whether the linked data forms a complete financial life.

This is judgment, not arithmetic — the reason it's an LLM and not another `if`:
a rule can check "salary exists", but deciding that a picture with a salary and
groceries yet no housing cost, no utilities, and big unexplained transfers-out
LOOKS like half a financial life requires world knowledge about how people live.

DESIGN NOTE: advisory-only by design. It never blocks (blocking stays
deterministic — see completeness.py), and if Gemini fails the coverage report
degrades to deterministic-only with an explicit notice, because a broken
advisory check should not lock the customer out of the app.
"""
import logging

from app.agents.gemini_client import audit_numbers, run_gemini_agent
from app.agents.schemas import SufficiencyOutput


logger = logging.getLogger("edraak.agents.data_sufficiency")

_BANK_ALIASES = {
    "مصرف الإنماء": ("مصرف الإنماء", "الإنماء"),
    "مصرف الراجحي": ("مصرف الراجحي", "الراجحي"),
    "البنك الأهلي السعودي": ("البنك الأهلي السعودي", "البنك الأهلي", "الأهلي"),
    "بنك الرياض": ("بنك الرياض",),
    "البنك السعودي الأول": ("البنك السعودي الأول", "ساب"),
}
_UNVERIFIED_BANK_FINDING = (
    "قد تكون بعض مصادر الدخل أو النفقات خارج الحسابات المرتبطة؛ "
    "لا يمكن تحديد البنك قبل موافقتك على الربط."
)

INSTRUCTION = """
You are the Edraak Data Sufficiency Agent.
You receive aggregate facts and a sample of recent transactions from the bank
accounts a customer has LINKED so far. Other accounts may exist that you cannot
see — under open banking you only see what the customer consented to share.
Your job: judge whether this picture looks like a COMPLETE financial life that a
12-month cash-flow simulation can trust, or a partial slice.
Do:
- Reason like a financial reviewer: a working adult normally shows housing costs
  (rent or mortgage or family home), utilities/telecom bills, groceries, and
  transport somewhere. Salary with almost no essential spending suggests the
  spending happens at an unlinked bank; heavy spending with weak income suggests
  the income arrives elsewhere.
- Watch for outbound transfers that look like they feed the customer's own other
  accounts, and for round recurring transfers with no visible purpose.
- Set looks_complete accordingly, with confidence 0-1.
- findings_ar: at most 3 short, specific Arabic observations, each actionable
  (what seems missing and why linking another bank would fix it). Mention only
  numbers that appear in the input.
- If the picture genuinely looks complete, say so in one reassuring finding.
Do not:
- Do not invent numbers, banks, or transactions.
- Never name or imply a specific unlinked bank. The evidence cannot establish
  that the customer owns an account at Al Rajhi, SNB, Riyad Bank, SAB, or any
  other institution before consent. Say "بنك آخر" or "حساب آخر" only.
- Do not repeat generic advice; tie every finding to the supplied evidence.
- Do not treat small noise accounts as meaningful gaps.
"""


def assess(evidence: dict) -> SufficiencyOutput:
    """Run the sufficiency judgment over the deterministic evidence payload."""
    output = run_gemini_agent("data_sufficiency", evidence, SufficiencyOutput, INSTRUCTION)
    output.findings_ar = _guard_unverified_bank_claims(
        output.findings_ar, evidence.get("connected_banks_ar", [])
    )
    audit_numbers("data_sufficiency", output.findings_ar, evidence)
    logger.info("flow.agent.data_sufficiency.completed looks_complete=%s confidence=%s findings=%s",
                output.looks_complete, output.confidence, len(output.findings_ar))
    return output


def _guard_unverified_bank_claims(findings: list[str], connected_banks_ar: list[str]) -> list[str]:
    """Replace any guessed unlinked-bank identity with an explicit uncertainty statement."""
    connected = set(connected_banks_ar)
    guarded = []
    for finding in findings:
        named_unlinked_bank = any(
            bank not in connected and any(alias in finding for alias in aliases)
            for bank, aliases in _BANK_ALIASES.items()
        )
        safe_finding = _UNVERIFIED_BANK_FINDING if named_unlinked_bank else finding
        if safe_finding not in guarded:
            guarded.append(safe_finding)
    return guarded
