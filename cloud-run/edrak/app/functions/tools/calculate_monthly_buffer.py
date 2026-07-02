def calculate_monthly_buffer(salary, monthly_obligations, new_installment, avg_flexible_spending):
    return round(salary - monthly_obligations - new_installment - avg_flexible_spending)
