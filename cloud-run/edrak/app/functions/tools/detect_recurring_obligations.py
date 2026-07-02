def detect_recurring_obligations(transactions, loans):
    recurring_expenses = sum(
        abs(transaction["amount"])
        for transaction in transactions
        if transaction["transaction_type"] == "expense" and transaction.get("is_recurring")
    )
    active_loan_installments = sum(
        loan["monthly_installment"]
        for loan in loans
        if loan["status"] == "active"
    )
    return round(recurring_expenses + active_loan_installments)
