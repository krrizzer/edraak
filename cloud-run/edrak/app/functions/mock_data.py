PROFILES = [
    {
        "user_id": "stable",
        "name_ar": "سارة العميلة المستقرة",
        "monthly_income": 18000,
        "current_balance": 42000,
        "savings": 65000,
        "monthly_obligations": 4200,
        "risk_preference_ar": "حذرة ومتوازنة",
        "behavior_summary_ar": "دخل ثابت، التزامات منخفضة، وادخار شهري منتظم.",
        "spending_categories": {
            "السكن": 4200,
            "المعيشة": 2800,
            "النقل": 900,
            "الترفيه": 1200,
            "الادخار": 3500,
        },
        "avg_flexible_spending": 3200,
    },
    {
        "user_id": "overcommitted",
        "name_ar": "خالد الملتزم بأقساط عالية",
        "monthly_income": 14500,
        "current_balance": 8500,
        "savings": 12000,
        "monthly_obligations": 8200,
        "risk_preference_ar": "يميل لاتخاذ قرارات سريعة",
        "behavior_summary_ar": "نسبة الالتزامات مرتفعة والمرونة الشهرية محدودة.",
        "spending_categories": {
            "السكن": 4800,
            "قروض قائمة": 3400,
            "المعيشة": 3100,
            "النقل": 1300,
            "الترفيه": 1700,
        },
        "avg_flexible_spending": 3000,
    },
    {
        "user_id": "high_spender",
        "name_ar": "نورة ذات الدخل العالي والإنفاق العالي",
        "monthly_income": 32000,
        "current_balance": 26000,
        "savings": 48000,
        "monthly_obligations": 9300,
        "risk_preference_ar": "مرنة وتقبل المخاطرة المحسوبة",
        "behavior_summary_ar": "دخل عال لكن الإنفاق المرن يستهلك جزءا كبيرا من الفائض.",
        "spending_categories": {
            "السكن": 7600,
            "قروض قائمة": 1700,
            "المعيشة": 5200,
            "السفر": 4800,
            "الترفيه": 3900,
            "الادخار": 3000,
        },
        "avg_flexible_spending": 9700,
    },
]

TRANSACTIONS = {
    "stable": [
        {"date": "2026-06-01", "description_ar": "راتب شهري", "amount": 18000, "category_ar": "دخل"},
        {"date": "2026-06-03", "description_ar": "إيجار", "amount": -4200, "category_ar": "السكن"},
        {"date": "2026-06-07", "description_ar": "مشتريات أساسية", "amount": -850, "category_ar": "المعيشة"},
        {"date": "2026-06-12", "description_ar": "تحويل إلى الادخار", "amount": -3500, "category_ar": "ادخار"},
        {"date": "2026-06-19", "description_ar": "مطاعم وترفيه", "amount": -420, "category_ar": "ترفيه"},
    ],
    "overcommitted": [
        {"date": "2026-06-01", "description_ar": "راتب شهري", "amount": 14500, "category_ar": "دخل"},
        {"date": "2026-06-02", "description_ar": "إيجار", "amount": -4800, "category_ar": "السكن"},
        {"date": "2026-06-05", "description_ar": "قسط تمويل قائم", "amount": -3400, "category_ar": "قروض"},
        {"date": "2026-06-10", "description_ar": "مشتريات أساسية", "amount": -1200, "category_ar": "المعيشة"},
        {"date": "2026-06-22", "description_ar": "ترفيه", "amount": -650, "category_ar": "ترفيه"},
    ],
    "high_spender": [
        {"date": "2026-06-01", "description_ar": "راتب شهري", "amount": 32000, "category_ar": "دخل"},
        {"date": "2026-06-03", "description_ar": "إيجار", "amount": -7600, "category_ar": "السكن"},
        {"date": "2026-06-08", "description_ar": "حجز سفر", "amount": -4200, "category_ar": "السفر"},
        {"date": "2026-06-14", "description_ar": "مطاعم", "amount": -1800, "category_ar": "ترفيه"},
        {"date": "2026-06-25", "description_ar": "تحويل إلى الادخار", "amount": -3000, "category_ar": "ادخار"},
    ],
}


def get_profiles():
    return PROFILES


def get_profile_by_id(user_id):
    return next((profile for profile in PROFILES if profile["user_id"] == user_id), None)


def get_transactions_by_user(user_id):
    return TRANSACTIONS.get(user_id, [])
