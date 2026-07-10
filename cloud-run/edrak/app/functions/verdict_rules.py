"""Deterministic verdict over the forecast curve. The LLM never chooses the verdict."""
from typing import Callable

from app.functions.forecast_engine import ForecastResult


# All tunable thresholds in one place. The verdict logic below reads only these.
THRESHOLDS = {
    # Rule 1: a shortfall inside this window with almost no savings means avoid.
    "early_shortfall_window_months": 3,
    # Rule 1: months of savings cover below this makes an early shortfall fatal.
    "min_savings_cover_for_delay": 1.0,
    # Caution triggers when no shortfall exists but the curve peaks above this ratio (%).
    "ratio_peak_caution": 45.0,
    # Caution triggers when savings cover fewer months than this at the worst point.
    "savings_cover_caution": 2.0,
    # Caution triggers when the ML probability of a missed payment exceeds this.
    "risk_probability_caution": 0.5,
    # How many months ahead we search for a clean start before giving up on delay.
    "max_delay_months": 12,
}

# Modern, natural Arabic verdict labels (kept in sync with schemas.Recommendation).
VERDICT_PROCEED = "قرار آمن"
VERDICT_CAUTION = "مقبول بحذر"
VERDICT_DELAY = "الأفضل تأجيله"
VERDICT_AVOID = "غير مناسب"


def decide_verdict(forecast: ForecastResult, risk_probability: float,
                   resimulate: Callable[[int], ForecastResult]) -> dict:
    """Apply the rule ladder to the forecast curve and return verdict + reasons.

    resimulate(offset) must rebuild the forecast as if the customer waits
    `offset` months — the engine's start_offset parameter does exactly that.
    """
    t = THRESHOLDS
    early_window = t["early_shortfall_window_months"]
    has_early_shortfall = (
        forecast.first_shortfall_month is not None
        and forecast.first_shortfall_month <= early_window
    )

    if has_early_shortfall and forecast.months_of_savings_cover < t["min_savings_cover_for_delay"]:
        return _verdict(VERDICT_AVOID, None, ["early_shortfall_no_savings"])

    if forecast.first_shortfall_month is not None:
        ready = _first_clean_start(resimulate, t["max_delay_months"])
        if ready is not None:
            return _verdict(VERDICT_DELAY, ready, ["temporary_overlap_ends"])
        return _verdict(VERDICT_AVOID, None, ["structural_shortfall"])

    reasons = []
    if forecast.obligation_ratio_peak >= t["ratio_peak_caution"]:
        reasons.append("high_peak_obligation_ratio")
    if forecast.months_of_savings_cover < t["savings_cover_caution"]:
        reasons.append("thin_savings_cover")
    if risk_probability >= t["risk_probability_caution"]:
        reasons.append("elevated_risk_probability")
    if reasons:
        return _verdict(VERDICT_CAUTION, None, reasons)

    return _verdict(VERDICT_PROCEED, None, ["clean_curve"])


def _first_clean_start(resimulate: Callable[[int], ForecastResult], max_months: int) -> int | None:
    """Find the smallest wait (in months) after which a fresh 12-month run has no shortfall."""
    for wait in range(1, max_months + 1):
        if resimulate(wait).first_shortfall_month is None:
            return wait
    return None


def _verdict(verdict: str, ready_in_months: int | None, reason_tags: list[str]) -> dict:
    """Package the verdict result the pipeline and Decision Advisor consume."""
    return {
        "verdict": verdict,
        "ready_in_months": ready_in_months,
        "reason_tags": reason_tags,
    }
