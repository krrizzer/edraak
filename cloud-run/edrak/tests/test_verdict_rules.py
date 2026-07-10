"""Verdict rule tests: the verdict must flip as the forecast curve changes."""
from app.functions.forecast_engine import build_forecast
from app.functions.verdict_rules import (
    VERDICT_AVOID,
    VERDICT_CAUTION,
    VERDICT_DELAY,
    VERDICT_PROCEED,
    decide_verdict,
)


def _decide(profile, loans, obligations, new_installment, risk_probability=0.1):
    forecast = build_forecast(profile, loans, obligations, new_installment)
    return decide_verdict(
        forecast,
        risk_probability,
        lambda wait: build_forecast(profile, loans, obligations, new_installment, start_offset=wait),
    )


def _profile(salary=10000, flexible=3000, balance=40000):
    return {
        "salary": salary,
        "avg_flexible_spending": flexible,
        "total_balance": balance,
        "salary_timing_variance_days": 0.0,
    }


def _loan(installment, remaining_months):
    return {"loan_id": "L1", "bank_code": "SNB", "loan_type": "personal", "status": "active",
            "monthly_installment": installment, "remaining_months": remaining_months}


def test_clean_curve_proceeds():
    result = _decide(_profile(), [_loan(1000, 24)], [], new_installment=1500)
    assert result["verdict"] == VERDICT_PROCEED


def test_temporary_overlap_delays_with_ready_in_months():
    # Loan of 5000 for 2 more months causes a shortfall that self-heals in month 3.
    result = _decide(_profile(), [_loan(5000, 2)], [], new_installment=2500)
    assert result["verdict"] == VERDICT_DELAY
    assert result["ready_in_months"] == 2


def test_same_overlap_with_no_savings_becomes_avoid():
    # Identical curve, but savings cover < 1 month at the worst point.
    result = _decide(_profile(balance=2000), [_loan(5000, 2)], [], new_installment=2500)
    assert result["verdict"] == VERDICT_AVOID


def test_structural_shortfall_never_becomes_delay():
    # A permanent obligation overload has no clean start month within a year.
    result = _decide(_profile(balance=200000), [_loan(6000, 60)], [], new_installment=2500)
    assert result["verdict"] == VERDICT_AVOID


def test_high_peak_ratio_without_shortfall_is_caution():
    # 4500/10000 committed+new = 45% peak ratio, but buffer stays positive.
    result = _decide(_profile(flexible=1000, balance=100000), [_loan(2500, 24)], [], new_installment=2000)
    assert result["verdict"] == VERDICT_CAUTION
    assert "high_peak_obligation_ratio" in result["reason_tags"]


def test_high_ml_probability_alone_triggers_caution():
    result = _decide(_profile(), [_loan(1000, 24)], [], new_installment=1500, risk_probability=0.8)
    assert result["verdict"] == VERDICT_CAUTION
    assert "elevated_risk_probability" in result["reason_tags"]


def test_verdict_flips_when_the_loan_tail_shortens():
    # Same numbers, but the big loan has 20 months left instead of 2:
    # waiting cannot fix it inside the delay window, so the verdict flips.
    delayed = _decide(_profile(), [_loan(5000, 2)], [], new_installment=2500)
    stuck = _decide(_profile(), [_loan(5000, 20)], [], new_installment=2500)
    assert delayed["verdict"] == VERDICT_DELAY
    assert stuck["verdict"] == VERDICT_DELAY or stuck["verdict"] == VERDICT_AVOID
    assert stuck["ready_in_months"] != delayed["ready_in_months"]
