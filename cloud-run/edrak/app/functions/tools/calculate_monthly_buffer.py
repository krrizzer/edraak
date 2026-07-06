def calculate_monthly_buffer(
    salary,
    recurring_obligations,
    monthly_loan_installments,
    avg_flexible_spending,
    new_installment,
):
    return round(
        salary
        - recurring_obligations
        - monthly_loan_installments
        - avg_flexible_spending
        - new_installment
    )
