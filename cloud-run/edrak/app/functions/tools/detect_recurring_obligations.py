def detect_recurring_obligations(transactions):
    recurring_expenses = sum(
        abs(transaction["amount"])
        for transaction in transactions
        if transaction["transaction_type"] == "expense" and transaction.get("is_recurring")
    )
    return round(recurring_expenses)
