"""Orchestration for both modes: deterministic steps and LLM agents, with an honest step trace.

Showing deterministic steps in the trace is a feature — the auditability pitch.
"""
import logging
import time

from app.agents.decision_advisor import advise
from app.agents.intervention import intervene
from app.agents.transaction_intelligence import detect_obligations
from app.data.bigquery_client import (
    get_accounts,
    get_customer_by_id,
    get_loans,
    get_transactions,
    save_alert,
    save_user_profile,
)
from app.functions.forecast_engine import build_forecast
from app.functions.profile_builder import build_user_profile
from app.functions.radar import run_radar
from app.functions.risk_model import predict_risk
from app.functions.validator import validate_inputs
from app.functions.verdict_rules import VERDICT_AVOID, decide_verdict


# When a shortfall is structural (avoid), floor the displayed risk so an absurd
# input can't show a mild-looking probability. Rules own the truth; this keeps
# the ML signal from contradicting an obvious "no".
STRUCTURAL_RISK_FLOOR = 0.95


logger = logging.getLogger("edraak.pipeline")


def run_analysis(decision_input: dict) -> dict:
    """Mode A: validator → transaction intelligence → forecast → verdict → risk model → advisor."""
    customer_id = decision_input["customer_id"]
    trace = _Trace()
    customer, accounts, transactions, loans = _load_sources(customer_id)

    validation = validate_inputs(customer, accounts, transactions, loans, decision_input)
    trace.add("validator", "deterministic", "فحص اكتمال البيانات واتساقها عبر البنوك.")
    if not validation["is_valid"]:
        logger.warning("flow.analysis.validation_failed customer_id=%s errors=%s", customer_id,
                       len(validation["blocking_errors_ar"]))
        raise ValueError("؛ ".join(validation["blocking_errors_ar"]))

    obligations, obligation_warnings, from_cache = detect_obligations(customer_id, transactions)
    trace.add("recurrence_detector", "deterministic",
              "تجميع المعاملات المتكررة حسب المبلغ واليوم عبر الأشهر لاكتشاف الالتزامات.")
    trace.add("transaction_intelligence", "llm",
              "تصنيف كل مجموعة متكررة (جمعية/تقسيط/إيجار/حوالة عائلية...)."
              + (" (من الذاكرة المؤقتة)" if from_cache else ""))

    profile = build_user_profile(customer, accounts, transactions, loans, obligations)
    save_user_profile(profile)

    new_installment = float(decision_input["monthly_installment"])
    duration = int(decision_input["duration_months"])
    down_payment = float(decision_input.get("down_payment") or 0)

    def simulate(wait: int):
        """Rebuild the forecast as if the customer starts the commitment `wait` months later."""
        return build_forecast(profile, loans, obligations, new_installment,
                              start_offset=wait, duration_months=duration, down_payment=down_payment)

    forecast = build_forecast(profile, loans, obligations, new_installment,
                              duration_months=duration, down_payment=down_payment)
    trace.add("forecast_engine", "deterministic",
              "محاكاة التدفق النقدي شهرًا بشهر لاثني عشر شهرًا عبر جميع البنوك.")

    risk_probability = predict_risk(_risk_features(forecast, profile, obligations, loans))
    trace.add("risk_model", "deterministic",
              "تقدير احتمالية التعثر خلال ستة أشهر بنموذج إحصائي مدرب.")

    verdict = decide_verdict(forecast, risk_probability, simulate)
    if verdict["verdict"] == VERDICT_AVOID and forecast.first_shortfall_month is not None:
        risk_probability = max(risk_probability, STRUCTURAL_RISK_FLOOR)
    trace.add("verdict_rules", "deterministic", "تطبيق قواعد القرار على منحنى التوقعات.")
    logger.info("flow.analysis.verdict customer_id=%s verdict=%s ready_in_months=%s risk_probability=%s",
                customer_id, verdict["verdict"], verdict["ready_in_months"], risk_probability)

    advisor_payload = {
        "customer": _customer_view(customer),
        "decision_input": decision_input,
        "verdict": verdict,
        "risk_probability": risk_probability,
        "forecast": forecast.to_dict(),
        "detected_obligations": obligations,
        "profile": profile,
        "validation_warnings_ar": validation["warnings_ar"] + obligation_warnings,
    }
    advisor = advise(advisor_payload)
    trace.add("decision_advisor", "llm", advisor.trace_message_ar)

    return {
        "customer": _customer_view(customer),
        "recommendation": advisor.recommendation,
        "ready_in_months": verdict["ready_in_months"],
        "reason_tags": verdict["reason_tags"],
        "risk_probability": risk_probability,
        "forecast": forecast.to_dict(),
        "detected_obligations_by_bank": _group_by_bank(obligations),
        "profile": _profile_view(profile),
        "explanation_ar": advisor.explanation_ar,
        "risk_factors_ar": advisor.risk_factors_ar,
        "safer_options_ar": advisor.safer_options_ar,
        "validation_warnings_ar": validation["warnings_ar"] + obligation_warnings,
        "step_trace": trace.steps,
    }


def run_radar_check(customer_id: str) -> dict:
    """Mode B: deterministic radar detection, then one intervention message."""
    trace = _Trace()
    customer, accounts, transactions, loans = _load_sources(customer_id)

    obligations, _, _ = detect_obligations(customer_id, transactions)
    profile = build_user_profile(customer, accounts, transactions, loans, obligations)

    detection = run_radar(profile, accounts, transactions, loans, obligations)
    trace.add("radar_detector", "deterministic",
              "مقارنة وتيرة الصرف الحالية بخط الأساس وإسقاط رصيد نهاية الشهر.")
    logger.info("flow.radar.completed customer_id=%s has_gap=%s gap=%s",
                customer_id, detection["has_gap"], detection["gap_amount"])

    intervention_payload = {
        "customer": _customer_view(customer),
        **detection,
    }
    alert_text = intervene(intervention_payload)
    trace.add("intervention_agent", "llm", alert_text.trace_message_ar)

    alert_id = None
    if detection["alert_type"] != "on_track":
        alert_id = save_alert({
            "customer_id": customer_id,
            "alert_type": detection["alert_type"],
            "gap_amount": detection["gap_amount"],
            "gap_date": detection["gap_date"],
            "cause_category": (detection["cause_category"] or {}).get("category"),
            "message_ar": alert_text.message_ar,
            "trajectory_json": _json(detection["trajectory"]),
        })

    return {
        "customer": _customer_view(customer),
        "has_gap": detection["has_gap"],
        "alert_type": detection["alert_type"],
        "gap_amount": detection["gap_amount"],
        "gap_date": detection["gap_date"],
        "cause_category": detection["cause_category"],
        "trajectory": detection["trajectory"],
        "title_ar": alert_text.title_ar,
        "message_ar": alert_text.message_ar,
        "alert_id": alert_id,
        "step_trace": trace.steps,
    }


def _load_sources(customer_id: str) -> tuple[dict, list[dict], list[dict], list[dict]]:
    """Load every cross-bank source table for one customer."""
    customer = get_customer_by_id(customer_id)
    if not customer:
        raise LookupError("Customer not found")
    return customer, get_accounts(customer_id), get_transactions(customer_id), get_loans(customer_id)


def _risk_features(forecast, profile: dict, obligations: list[dict], loans: list[dict]) -> dict:
    """Assemble the fixed feature dict the risk model expects."""
    salary = max(float(profile.get("salary") or 1), 1)
    banks = {l.get("bank_code") for l in loans if l.get("bank_code")}
    for ob in obligations:
        banks.update(ob.get("source_bank_codes") or [])
    return {
        "obligation_ratio_peak": forecast.obligation_ratio_peak,
        "min_buffer_over_income": forecast.min_buffer_value / salary,
        "salary_timing_variance_days": profile.get("salary_timing_variance_days") or 0,
        "bnpl_count": sum(1 for ob in obligations if ob.get("obligation_type") == "bnpl_installment"),
        "savings_cover_months": forecast.months_of_savings_cover,
        "banks_with_obligations": len(banks),
    }


def _group_by_bank(obligations: list[dict]) -> dict[str, list[dict]]:
    """Group detected obligations by source bank — the "what your bank can't see" panel."""
    grouped: dict[str, list[dict]] = {}
    for ob in obligations:
        bank = (ob.get("source_bank_codes") or ["UNKNOWN"])[0]
        grouped.setdefault(bank, []).append(ob)
    return grouped


def _customer_view(customer: dict) -> dict:
    return {
        "customer_id": customer["customer_id"],
        "ar_name": customer.get("ar_name"),
        "en_name": customer.get("en_name"),
    }


def _profile_view(profile: dict) -> dict:
    """The profile numbers the UI shows next to the forecast."""
    return {
        "salary": profile["salary"],
        "salary_day": profile["salary_day"],
        "salary_timing_variance_days": profile["salary_timing_variance_days"],
        "total_balance": profile["total_balance"],
        "banks_count": profile["banks_count"],
        "active_loans_count": profile["active_loans_count"],
        "monthly_loan_installments": profile["monthly_loan_installments"],
        "avg_monthly_spending": profile["avg_monthly_spending"],
        "avg_flexible_spending": profile["avg_flexible_spending"],
    }


class _Trace:
    """Collects the honest step trace shown in the UI."""

    def __init__(self) -> None:
        self.steps: list[dict] = []
        self._started = time.perf_counter()

    def add(self, step: str, kind: str, message_ar: str) -> None:
        """Record one completed step with elapsed time since the previous one."""
        now = time.perf_counter()
        self.steps.append({
            "step": step,
            "kind": kind,
            "status": "اكتمل",
            "message_ar": message_ar,
            "elapsed_ms": round((now - self._started) * 1000),
        })
        self._started = now


def _json(payload) -> str:
    import json

    return json.dumps(payload, ensure_ascii=False, default=str)
