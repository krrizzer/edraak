def categorize_spending(transactions):
    categories = {}
    for transaction in transactions:
        if transaction["transaction_type"] != "expense":
            continue
        category = transaction["category"]
        categories[category] = categories.get(category, 0) + abs(transaction["amount"])
    return {category: round(amount) for category, amount in categories.items()}
