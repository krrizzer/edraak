def calculate_obligation_ratio(monthly_obligations, salary):
    if salary <= 0:
        return 100
    return round((monthly_obligations / salary) * 100)
