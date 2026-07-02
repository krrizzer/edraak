from app.functions.mock_data import (
    get_active_loans_by_customer,
    get_customers,
    get_transactions_by_customer,
    now_iso,
    save_user_profiles,
)
from app.functions.tools import (
    calculate_obligation_ratio,
    categorize_spending,
    detect_recurring_obligations,
)

FLEXIBLE_CATEGORIES = {
    "restaurants",
    "shopping",
    "subscriptions",
    "travel",
    "entertainment",
    "bnpl",
}


def build_user_profile(customer, transactions, loans):
    spending_by_category = categorize_spending(transactions)
    monthly_loan_installments = sum(loan["monthly_installment"] for loan in loans)
    total_remaining_loans = sum(loan["remaining_amount"] for loan in loans)
    avg_monthly_spending = sum(spending_by_category.values())
    avg_flexible_spending = sum(
        amount
        for category, amount in spending_by_category.items()
        if category in FLEXIBLE_CATEGORIES
    )
    recurring_obligations = detect_recurring_obligations(transactions, loans)
    savings_estimate = max(customer["current_balance"] - recurring_obligations, 0)
    obligation_ratio = calculate_obligation_ratio(recurring_obligations, customer["salary"])

    if obligation_ratio >= 55:
        behavior_summary = "الالتزامات المتكررة مرتفعة وتحتاج مراقبة قبل إضافة التزام جديد."
        risk_preference = "حذر جدا"
    elif avg_flexible_spending > customer["salary"] * 0.25:
        behavior_summary = "الدخل جيد لكن الإنفاق المرن يستهلك جزءا واضحا من الفائض الشهري."
        risk_preference = "متوازن مع قابلية للمخاطرة"
    else:
        behavior_summary = "الالتزامات تحت السيطرة والفائض الشهري يسمح بتقييم قرارات جديدة بهدوء."
        risk_preference = "حذر ومتوازن"

    return {
        "customer_id": customer["customer_id"],
        "ar_name": customer["ar_name"],
        "en_name": customer["en_name"],
        "salary": customer["salary"],
        "current_balance": customer["current_balance"],
        "active_loans_count": len(loans),
        "total_remaining_loans": round(total_remaining_loans),
        "monthly_loan_installments": round(monthly_loan_installments),
        "avg_monthly_spending": round(avg_monthly_spending),
        "avg_flexible_spending": round(avg_flexible_spending),
        "recurring_obligations": recurring_obligations,
        "savings_estimate": round(savings_estimate),
        "obligation_ratio": obligation_ratio,
        "spending_behavior_summary_ar": behavior_summary,
        "risk_preference_estimate_ar": risk_preference,
        "profile_generated_at": now_iso(),
    }


def load_all_user_profiles():
    profiles = []
    for customer in get_customers():
        transactions = get_transactions_by_customer(customer["customer_id"])
        loans = get_active_loans_by_customer(customer["customer_id"])
        profiles.append(build_user_profile(customer, transactions, loans))
    save_user_profiles(profiles)
    return profiles


if __name__ == "__main__":
    loaded_profiles = load_all_user_profiles()
    print({"status": "completed", "profiles_loaded": len(loaded_profiles)})
