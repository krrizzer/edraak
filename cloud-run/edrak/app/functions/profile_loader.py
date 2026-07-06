import logging
from datetime import datetime

from app.functions.bigquery_data import (
    get_loans_from_bigquery,
    get_transactions_from_bigquery,
    list_customers_from_bigquery,
    save_user_profile_to_bigquery,
)
from app.functions.tools import calculate_obligation_ratio, categorize_spending, detect_recurring_obligations


logger = logging.getLogger("edraak.profile_loader")


def load_user_profiles_from_bigquery(customer_id=None):
    logger.info(
        "flow.profile_loader.start customer_id=%s message=Starting user_profiles generation from BigQuery source tables",
        customer_id or "ALL",
    )
    customers = list_customers_from_bigquery(customer_id)
    profiles = []

    for customer in customers:
        current_customer_id = customer["customer_id"]
        logger.info(
            "flow.profile_loader.customer.start customer_id=%s message=Reading transactions and active loans before calculating profile",
            current_customer_id,
        )
        transactions = get_transactions_from_bigquery(current_customer_id)
        loans = get_loans_from_bigquery(current_customer_id)
        profile = build_user_profile_from_sources(customer, transactions, loans)
        save_user_profile_to_bigquery(profile)
        profiles.append(profile)
        logger.info(
            "flow.profile_loader.customer.saved customer_id=%s transactions=%s loans=%s message=Generated and stored user_profiles row",
            current_customer_id,
            len(transactions),
            len(loans),
        )

    logger.info(
        "flow.profile_loader.completed profiles_loaded=%s message=Finished user_profiles generation",
        len(profiles),
    )
    return profiles


def build_user_profile_from_sources(customer, transactions, loans):
    salary = round(customer.get("salary") or 0)
    current_balance = round(customer.get("current_balance") or 0)
    active_loans = [loan for loan in loans if loan.get("status") == "active"]

    active_loans_count = len(active_loans)
    total_remaining_loans = round(sum(loan.get("remaining_amount") or 0 for loan in active_loans))
    monthly_loan_installments = round(sum(loan.get("monthly_installment") or 0 for loan in active_loans))

    expenses = [
        transaction
        for transaction in transactions
        if transaction.get("transaction_type") == "expense"
    ]
    distinct_months = {
        str(transaction.get("transaction_date", ""))[:7]
        for transaction in expenses
        if transaction.get("transaction_date")
    }
    month_count = max(len(distinct_months), 1)
    total_expenses = sum(abs(transaction.get("amount") or 0) for transaction in expenses)
    avg_monthly_spending = round(total_expenses / month_count)

    recurring_obligations = detect_recurring_obligations(transactions)
    category_totals = categorize_spending(transactions)
    flexible_categories = {"shopping", "restaurants", "travel", "entertainment", "luxury", "other"}
    flexible_total = sum(
        amount
        for category, amount in category_totals.items()
        if str(category).lower() in flexible_categories
    )
    avg_flexible_spending = round(flexible_total / month_count)
    savings_estimate = round(current_balance + max(salary - avg_monthly_spending - monthly_loan_installments, 0))
    obligation_ratio = calculate_obligation_ratio(recurring_obligations + monthly_loan_installments, salary)

    return {
        "customer_id": customer["customer_id"],
        "ar_name": customer.get("ar_name"),
        "en_name": customer.get("en_name"),
        "salary": salary,
        "current_balance": current_balance,
        "active_loans_count": active_loans_count,
        "total_remaining_loans": total_remaining_loans,
        "monthly_loan_installments": monthly_loan_installments,
        "avg_monthly_spending": avg_monthly_spending,
        "avg_flexible_spending": avg_flexible_spending,
        "recurring_obligations": recurring_obligations,
        "savings_estimate": savings_estimate,
        "obligation_ratio": obligation_ratio,
        "spending_behavior_summary_ar": _spending_summary(avg_flexible_spending, salary, recurring_obligations),
        "risk_preference_estimate_ar": _risk_preference(obligation_ratio, savings_estimate, salary),
        "profile_generated_at": datetime.utcnow().isoformat(),
    }


def _spending_summary(avg_flexible_spending, salary, recurring_obligations):
    flexible_ratio = avg_flexible_spending / max(salary, 1)
    if flexible_ratio >= 0.3:
        return "الإنفاق المرن مرتفع مقارنة بالدخل ويحتاج إلى ضبط قبل إضافة التزام جديد."
    if recurring_obligations >= salary * 0.25:
        return "الالتزامات المتكررة مؤثرة على الدخل الشهري وتحتاج متابعة."
    return "سلوك الإنفاق يبدو متوازنًا بناءً على المعاملات المتاحة."


def _risk_preference(obligation_ratio, savings_estimate, salary):
    if obligation_ratio >= 45 or savings_estimate < salary:
        return "حساسية عالية للمخاطر بسبب الالتزامات أو انخفاض الاحتياطي."
    if obligation_ratio >= 30:
        return "حساسية متوسطة للمخاطر مع حاجة لمراقبة الالتزامات."
    return "قدرة جيدة على تحمل المخاطر ضمن الحدود المحسوبة."
