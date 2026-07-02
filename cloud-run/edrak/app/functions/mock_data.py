from datetime import datetime


CUSTOMERS = [
    {
        "customer_id": "CUST001",
        "username_en": "fahad",
        "ar_name": "فهد",
        "en_name": "Fahad",
        "national_id": "1000000001",
        "birthday": "1990-04-12",
        "salary": 16500,
        "current_balance": 28500,
        "created_at": "2026-06-01T09:00:00Z",
    },
    {
        "customer_id": "CUST002",
        "username_en": "sara",
        "ar_name": "سارة",
        "en_name": "Sara",
        "national_id": "1000000002",
        "birthday": "1988-11-20",
        "salary": 22000,
        "current_balance": 76000,
        "created_at": "2026-06-01T09:00:00Z",
    },
    {
        "customer_id": "CUST003",
        "username_en": "khalid",
        "ar_name": "خالد",
        "en_name": "Khalid",
        "national_id": "1000000003",
        "birthday": "1994-02-05",
        "salary": 14500,
        "current_balance": 9200,
        "created_at": "2026-06-01T09:00:00Z",
    },
]


TRANSACTIONS = [
    {
        "transaction_id": "TXN001",
        "customer_id": "CUST001",
        "transaction_date": "2026-06-01",
        "merchant": "Employer",
        "category": "salary",
        "amount": 16500,
        "transaction_type": "income",
        "is_recurring": True,
        "created_at": "2026-06-01T09:00:00Z",
    },
    {
        "transaction_id": "TXN002",
        "customer_id": "CUST001",
        "transaction_date": "2026-06-03",
        "merchant": "Landlord",
        "category": "rent",
        "amount": -4200,
        "transaction_type": "expense",
        "is_recurring": True,
        "created_at": "2026-06-03T09:00:00Z",
    },
    {
        "transaction_id": "TXN003",
        "customer_id": "CUST001",
        "transaction_date": "2026-06-07",
        "merchant": "Hypermarket",
        "category": "groceries",
        "amount": -950,
        "transaction_type": "expense",
        "is_recurring": False,
        "created_at": "2026-06-07T09:00:00Z",
    },
    {
        "transaction_id": "TXN004",
        "customer_id": "CUST001",
        "transaction_date": "2026-06-14",
        "merchant": "Restaurant",
        "category": "restaurants",
        "amount": -720,
        "transaction_type": "expense",
        "is_recurring": False,
        "created_at": "2026-06-14T09:00:00Z",
    },
    {
        "transaction_id": "TXN005",
        "customer_id": "CUST001",
        "transaction_date": "2026-06-20",
        "merchant": "Fuel Station",
        "category": "transport",
        "amount": -510,
        "transaction_type": "expense",
        "is_recurring": False,
        "created_at": "2026-06-20T09:00:00Z",
    },
    {
        "transaction_id": "TXN006",
        "customer_id": "CUST002",
        "transaction_date": "2026-06-01",
        "merchant": "Employer",
        "category": "salary",
        "amount": 22000,
        "transaction_type": "income",
        "is_recurring": True,
        "created_at": "2026-06-01T09:00:00Z",
    },
    {
        "transaction_id": "TXN007",
        "customer_id": "CUST002",
        "transaction_date": "2026-06-03",
        "merchant": "Utilities Provider",
        "category": "utilities",
        "amount": -700,
        "transaction_type": "expense",
        "is_recurring": True,
        "created_at": "2026-06-03T09:00:00Z",
    },
    {
        "transaction_id": "TXN008",
        "customer_id": "CUST002",
        "transaction_date": "2026-06-08",
        "merchant": "Investment Transfer",
        "category": "transfer",
        "amount": -4500,
        "transaction_type": "transfer",
        "is_recurring": True,
        "created_at": "2026-06-08T09:00:00Z",
    },
    {
        "transaction_id": "TXN009",
        "customer_id": "CUST002",
        "transaction_date": "2026-06-12",
        "merchant": "Subscriptions",
        "category": "subscriptions",
        "amount": -390,
        "transaction_type": "expense",
        "is_recurring": True,
        "created_at": "2026-06-12T09:00:00Z",
    },
    {
        "transaction_id": "TXN010",
        "customer_id": "CUST002",
        "transaction_date": "2026-06-18",
        "merchant": "Mall",
        "category": "shopping",
        "amount": -1800,
        "transaction_type": "expense",
        "is_recurring": False,
        "created_at": "2026-06-18T09:00:00Z",
    },
    {
        "transaction_id": "TXN011",
        "customer_id": "CUST003",
        "transaction_date": "2026-06-01",
        "merchant": "Employer",
        "category": "salary",
        "amount": 14500,
        "transaction_type": "income",
        "is_recurring": True,
        "created_at": "2026-06-01T09:00:00Z",
    },
    {
        "transaction_id": "TXN012",
        "customer_id": "CUST003",
        "transaction_date": "2026-06-02",
        "merchant": "Landlord",
        "category": "rent",
        "amount": -4800,
        "transaction_type": "expense",
        "is_recurring": True,
        "created_at": "2026-06-02T09:00:00Z",
    },
    {
        "transaction_id": "TXN013",
        "customer_id": "CUST003",
        "transaction_date": "2026-06-05",
        "merchant": "BNPL Provider",
        "category": "bnpl",
        "amount": -1400,
        "transaction_type": "expense",
        "is_recurring": True,
        "created_at": "2026-06-05T09:00:00Z",
    },
    {
        "transaction_id": "TXN014",
        "customer_id": "CUST003",
        "transaction_date": "2026-06-10",
        "merchant": "Hypermarket",
        "category": "groceries",
        "amount": -1250,
        "transaction_type": "expense",
        "is_recurring": False,
        "created_at": "2026-06-10T09:00:00Z",
    },
    {
        "transaction_id": "TXN015",
        "customer_id": "CUST003",
        "transaction_date": "2026-06-21",
        "merchant": "Clinic",
        "category": "emergency",
        "amount": -2300,
        "transaction_type": "expense",
        "is_recurring": False,
        "created_at": "2026-06-21T09:00:00Z",
    },
]


LOANS = [
    {
        "loan_id": "LOAN001",
        "customer_id": "CUST001",
        "loan_type": "car",
        "loan_total_amount": 90000,
        "total_profit_amount": 18000,
        "total_amount": 108000,
        "remaining_amount": 65000,
        "monthly_installment": 2300,
        "start_date": "2024-01-01",
        "end_date": "2028-01-01",
        "status": "active",
        "created_at": "2024-01-01T09:00:00Z",
    },
    {
        "loan_id": "LOAN002",
        "customer_id": "CUST002",
        "loan_type": "home",
        "loan_total_amount": 450000,
        "total_profit_amount": 135000,
        "total_amount": 585000,
        "remaining_amount": 390000,
        "monthly_installment": 5200,
        "start_date": "2022-05-01",
        "end_date": "2032-05-01",
        "status": "active",
        "created_at": "2022-05-01T09:00:00Z",
    },
    {
        "loan_id": "LOAN003",
        "customer_id": "CUST003",
        "loan_type": "personal_finance",
        "loan_total_amount": 70000,
        "total_profit_amount": 14000,
        "total_amount": 84000,
        "remaining_amount": 58000,
        "monthly_installment": 3100,
        "start_date": "2025-03-01",
        "end_date": "2028-03-01",
        "status": "active",
        "created_at": "2025-03-01T09:00:00Z",
    },
    {
        "loan_id": "LOAN004",
        "customer_id": "CUST003",
        "loan_type": "closed_car",
        "loan_total_amount": 52000,
        "total_profit_amount": 8000,
        "total_amount": 60000,
        "remaining_amount": 0,
        "monthly_installment": 0,
        "start_date": "2021-01-01",
        "end_date": "2024-01-01",
        "status": "closed",
        "created_at": "2021-01-01T09:00:00Z",
    },
]


USER_PROFILES = {}


def now_iso():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def get_customers():
    return CUSTOMERS


def get_customer_by_username(username):
    username = username.strip().lower()
    return next((customer for customer in CUSTOMERS if customer["username_en"] == username), None)


def get_customer_by_id(customer_id):
    return next((customer for customer in CUSTOMERS if customer["customer_id"] == customer_id), None)


def get_transactions_by_customer(customer_id):
    return [transaction for transaction in TRANSACTIONS if transaction["customer_id"] == customer_id]


def get_loans_by_customer(customer_id):
    return [loan for loan in LOANS if loan["customer_id"] == customer_id]


def get_active_loans_by_customer(customer_id):
    return [
        loan
        for loan in LOANS
        if loan["customer_id"] == customer_id and loan["status"] == "active"
    ]


def save_user_profile(profile):
    USER_PROFILES[profile["customer_id"]] = profile
    return profile


def get_user_profile(customer_id):
    return USER_PROFILES.get(customer_id)


def save_user_profiles(profiles):
    for profile in profiles:
        save_user_profile(profile)
    return profiles
