"""Forecast engine tests: the time dimension must behave exactly as designed."""
from app.functions.forecast_engine import build_forecast


def _profile(salary=10000, flexible=3000, balance=20000, variance=0.0, spending_std=0):
    return {
        "salary": salary,
        "avg_flexible_spending": flexible,
        "total_balance": balance,
        "salary_timing_variance_days": variance,
        "monthly_spending_std": spending_std,
    }


def _loan(installment, remaining_months, bank="SNB"):
    return {
        "loan_id": "L1",
        "bank_code": bank,
        "loan_type": "personal",
        "monthly_installment": installment,
        "remaining_months": remaining_months,
        "status": "active",
    }


def _obligation(kind, amount, remaining=None, day=10, committed=True):
    return {
        "obligation_type": kind,
        "counterparty": kind,
        "monthly_amount": amount,
        "day_of_month": day,
        "remaining_months": remaining,
        "confidence": 0.9,
        "is_committed": committed,
    }


def test_loan_with_one_remaining_month_vanishes_from_month_2():
    forecast = build_forecast(_profile(), [_loan(2000, 1)], [])
    assert forecast.months[0].committed == 2000
    assert forecast.months[1].committed == 0
    # The freed installment is annotated on the month it disappears.
    released = forecast.months[1].events
    assert any(e["type"] == "obligation_released" and e["amount"] == 2000 for e in released)


def test_bnpl_with_two_remaining_pays_months_1_and_2_only():
    forecast = build_forecast(_profile(), [], [_obligation("bnpl_installment", 450, remaining=2)])
    assert [p.committed for p in forecast.months[:3]] == [450, 450, 0]


def test_ongoing_obligation_without_remaining_months_never_ends():
    forecast = build_forecast(_profile(), [], [_obligation("rent", 4000)])
    assert all(p.committed == 4000 for p in forecast.months)


def test_obligation_ratio_is_a_curve_that_drops_when_loan_ends():
    forecast = build_forecast(_profile(), [_loan(3000, 2)], [], new_installment=1000)
    assert forecast.months[1].obligation_ratio == 40.0  # (3000 + 1000) / 10000
    assert forecast.months[2].obligation_ratio == 10.0  # loan gone from month 3
    assert forecast.obligation_ratio_peak == 40.0
    assert forecast.obligation_ratio_month_12 == 10.0


def test_first_shortfall_detected_with_amount():
    # 10000 - 5000 committed - 3000 flexible - 2500 new = -500 while the loan runs.
    forecast = build_forecast(_profile(), [_loan(5000, 2)], [], new_installment=2500)
    assert forecast.first_shortfall_month == 1
    assert forecast.first_shortfall_amount == 500
    assert forecast.months[2].buffer > 0  # loan ends, buffer recovers


def test_start_offset_simulates_waiting_out_a_temporary_overlap():
    loans = [_loan(5000, 2)]
    stressed = build_forecast(_profile(), loans, [], new_installment=2500)
    assert stressed.first_shortfall_month is not None
    waited = build_forecast(_profile(), loans, [], new_installment=2500, start_offset=2)
    assert waited.first_shortfall_month is None


def test_uncommitted_and_noncommitted_types_are_ignored():
    obligations = [
        _obligation("flexible_spending", 900),
        _obligation("one_off", 1200),
        _obligation("salary", 10000),
        _obligation("loan_installment_other_bank", 2200),  # covered by loans table
        _obligation("jamiya", 500, committed=False),
    ]
    forecast = build_forecast(_profile(), [], obligations)
    assert all(p.committed == 0 for p in forecast.months)


def test_projected_savings_accumulates_the_buffer():
    forecast = build_forecast(_profile(salary=10000, flexible=3000, balance=1000), [], [])
    assert forecast.months[0].projected_savings == 8000   # 1000 + 7000 buffer
    assert forecast.months[1].projected_savings == 15000


def test_salary_timing_variance_flag():
    calm = build_forecast(_profile(variance=1.0), [], [])
    jumpy = build_forecast(_profile(variance=3.5), [], [])
    assert calm.salary_timing_variance is False
    assert jumpy.salary_timing_variance is True


def test_stress_events_tag_temporary_overlap():
    forecast = build_forecast(_profile(), [_loan(5000, 2)], [], new_installment=2500)
    assert forecast.stress_events
    assert forecast.stress_events[0]["cause"] == "temporary_overlap"
    assert forecast.stress_events[0]["month"] == 1


def test_duration_months_stops_the_new_installment():
    # A 3-month commitment must not be charged for all 12 forecast months.
    forecast = build_forecast(_profile(), [], [], new_installment=2000, duration_months=3)
    assert [p.new_commitment for p in forecast.months[:5]] == [2000, 2000, 2000, 0, 0]
    assert forecast.months[0].buffer == 5000   # 10000 - 2000 - 3000
    assert forecast.months[3].buffer == 7000   # installment gone


def test_down_payment_lowers_starting_savings():
    without = build_forecast(_profile(balance=20000), [], [], new_installment=0)
    withdp = build_forecast(_profile(balance=20000), [], [], new_installment=0, down_payment=8000)
    assert withdp.months[0].projected_savings == without.months[0].projected_savings - 8000


def test_uncertainty_band_widens_by_spending_volatility():
    forecast = build_forecast(_profile(spending_std=600), [], [], new_installment=0)
    point = forecast.months[0]
    assert point.buffer_low == point.buffer - 600
    assert point.buffer_high == point.buffer + 600


def test_zero_volatility_gives_a_flat_band():
    point = build_forecast(_profile(spending_std=0), [], [], new_installment=0).months[0]
    assert point.buffer_low == point.buffer == point.buffer_high
