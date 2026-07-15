"""Generate synthetic cross-bank demo data with realistically messy transaction descriptions.

Demo bank layout per customer:
  - HOST bank = ALINMA: the initially visible salary account and daily spending.
  - Every external account, loan, and transaction is stored under ALRAJHI.
    One consent therefore reveals the complete cross-bank demo story.
  - Other bank tiles remain in the UI for realism but contain no seeded rows.
"""
import hashlib
import random
from calendar import monthrange
from datetime import date, datetime, timezone


# All seed dates are RELATIVE to the run date so the radar demo works whenever
# the data is loaded. Six full months of history plus the current month-to-date.
HISTORY_MONTHS = 6

HOST_BANK = "ALINMA"

BANKS = {
    "ALINMA": "مصرف الإنماء",
    "ALRAJHI": "مصرف الراجحي",
    "SNB": "البنك الأهلي السعودي",
    "RIYAD": "بنك الرياض",
    "SAB": "البنك السعودي الأول",
}


def generate_all(today: date | None = None) -> dict[str, list[dict]]:
    """Build every seed table as plain row dicts keyed by table name."""
    today = today or date.today()
    rng = random.Random(4471)
    specs = [
        _fahad_spec(),
        _sara_spec(),
        _khalid_spec(),
        _noura_spec(),
        _abdullah_spec(),
    ]

    customers, accounts, loans, transactions = [], [], [], []
    for spec in specs:
        rows = _render_transactions(spec, today, rng)
        _tune_radar_balance(spec, today, rows)
        _tune_trough_balance(spec, today, rows)
        for row in rows:
            row.pop("_flex", None)
        customers.append(spec["customer"])
        accounts.extend(spec["accounts"])
        loans.extend(_render_loans(spec, today))
        transactions.extend(rows)
    tables = {
        "customers": customers,
        "accounts": accounts,
        "loans": loans,
        "transactions": transactions,
    }
    _consolidate_external_banks(tables)
    return tables


def _consolidate_external_banks(tables: dict[str, list[dict]]) -> None:
    """Put every non-host source row in Al Rajhi for the one-link demo path."""
    for account in tables["accounts"]:
        if account["bank_code"] != HOST_BANK:
            account["bank_code"] = "ALRAJHI"
            account["bank_name_ar"] = BANKS["ALRAJHI"]
    for table_name in ("loans", "transactions"):
        for row in tables[table_name]:
            if row["bank_code"] != HOST_BANK:
                row["bank_code"] = "ALRAJHI"


def _fahad_spec() -> dict:
    """Family provider: credible at Alinma, temporarily squeezed after Al Rajhi is linked."""
    return {
        "customer": _customer("CUST001", "fahad", "فهد", "Fahad", "1000000001",
                              date(1990, 4, 12), 16500, "Riyadh", "Private", "Najd Logistics Co."),
        "accounts": [
            _account("ACC001-INM", "CUST001", "ALINMA", "current", 17800, True),
            _account("ACC001-INMS", "CUST001", "ALINMA", "savings", 8100, False),
            _account("ACC001-RAJ", "CUST001", "ALRAJHI", "current", 6400, False),
            _account("ACC001-RAJS", "CUST001", "ALRAJHI", "savings", 3500, False),
        ],
        "loans": [
            {"loan_id": "LN001", "bank_code": "ALRAJHI", "loan_type": "personal", "total": 79200,
             "installment": 2200, "remaining_months": 2, "months_paid": 34, "day": 27},
        ],
        "salary": {"amount": 16500, "day": 25, "bank": "ALINMA",
                   "day_overrides": {3: 29, 5: 28},
                   "descs": ["MUDAD PAYROLL NAJD LOGISTICS", "حوالة راتب - مداد", "SALARY TRF NAJD LOG CO"]},
        "recurring": [
            _item("rent", "ALINMA", 3, -4500, ["SADAD RENT EJAR PLATFORM", "ايجار - منصة إيجار"], None, "housing"),
            _item("family", "ALINMA", 26, -1500, ["حوالة صادرة - ابو فهد", "TRF TO ABU FAHAD 0501XXXXXX"], None, "transfer"),
            _item("netflix", "ALINMA", 8, -65, ["NETFLIX.COM AMSTERDAM NL"], "Netflix", "subscription"),
            _item("stc", "ALINMA", 10, -320, ["SADAD BILL - STC", "سداد - فاتورة STC"], "STC", None, jitter=0.05),
            _item("kahraba", "ALINMA", 15, -280, ["SADAD BILL - KAHRABA", "سداد - شركة الكهرباء"], None, "bills", jitter=0.2),
            _item("internet", "ALINMA", 11, -230, ["SADAD BILL - SALAM HOME INTERNET"], "Salam", "bills", jitter=0.03),
            _item("loan_raj", "ALRAJHI", 27, -2200, ["ARB PERSONAL FIN INSTALLMENT {n2}/36", "قسط تمويل شخصي - الراجحي"], None, None,
                  months_paid=34),
            _item("tabby1", "ALRAJHI", 12, -450, ["POS TABBY* PAYMENT RUH", "TABBY *INSTALMENT {n} OF 4"], None, None,
                  bnpl_total=4, bnpl_paid=2),
            _item("jamiya", "ALRAJHI", 5, -1000, ["حوالة داخلية - جمعية شهر {hijri}", "حوالة - جمعية الحي"], None, None),
            _item("tamara", "ALRAJHI", 18, -380, ["تمارا - قسط {n} من 4", "TAMARA PAYMENT ARB"], None, None,
                  bnpl_total=4, bnpl_paid=2),
            _item("tabby2", "ALRAJHI", 20, -300, ["TABBY *{n} OF 6 INSTAL", "POS TABBY PAYMENT"], None, None,
                  bnpl_total=6, bnpl_paid=3),
        ],
        "flexible": {
            "groceries": {"monthly": 1500, "count": 7, "bank": "ALINMA",
                          "descs": ["POS PANDA RETAIL RIYADH", "POS TAMIMI MARKETS 112", "POS OTHAIM MRKT"]},
            "cafes": {"monthly": 450, "count": 8, "bank": "ALINMA",
                      "descs": ["POS BARNS COFFEE 4421 RIYADH", "POS HALF MILLION RUH", "مقهى دوز - رياض"]},
            "restaurants": {"monthly": 750, "count": 5, "bank": "ALINMA",
                            "descs": ["POS ALBAIK KHURAIS RD", "HUNGERSTATION RIYADH", "POS SHAWARMA HOUSE"]},
            "entertainment": {"monthly": 250, "count": 2, "bank": "ALRAJHI",
                              "descs": ["VOX CINEMAS RIYADH FRONT", "POS PLAYSTATION NETWORK"]},
            "fuel": {"monthly": 500, "count": 5, "bank": "ALINMA",
                     "descs": ["POS SASCO FUEL 0091", "POS ALDREES PETROL"]},
            "shopping": {"monthly": 750, "count": 3, "bank": "ALRAJHI",
                         "descs": ["POS AMAZON.SA RETAIL", "POS EXTRA STORES RUH", "POS ZARA GRANADA MALL"]},
            "transport": {"monthly": 120, "count": 3, "bank": "ALRAJHI",
                          "descs": ["UBER TRIP HELP.UBER.COM", "POS CAREEM RIDE"]},
            "healthcare": {"monthly": 180, "count": 2, "bank": "ALINMA",
                           "descs": ["POS NAHDI PHARMACY 233", "POS ALHABIB CLINIC COPAY"]},
        },
        "events": [
            _event(-4, 17, -1200, "ALRAJHI", "POS PETROMIN CAR SERVICE RUH", "Petromin"),
            _event(-3, 25, 4000, "ALINMA", "ANNUAL PERFORMANCE BONUS NAJD LOGISTICS", "Employer"),
            _event(-2, 9, -650, "ALINMA", "POS DALLAH HOSPITAL COPAY", "Dallah Hospital"),
            _event(-1, 22, -1800, "ALRAJHI", "POS EXTRA STORES HOME APPLIANCE", "eXtra"),
        ],
        "current_month_pace": {},
    }


def _legacy_sara_spec() -> dict:
    """Healthy customer: strong salary, one host-bank car loan, no BNPL — the safe case."""
    return {
        "customer": _customer("CUST002", "sara", "سارة", "Sara", "1000000002",
                              date(1988, 11, 20), 22000, "Jeddah", "Government", "Ministry Entity"),
        "accounts": [
            _account("ACC002-INM", "CUST002", "ALINMA", "current", 54000, True),
            _account("ACC002-INMS", "CUST002", "ALINMA", "savings", 35000, False),
            _account("ACC002-RAJ", "CUST002", "ALRAJHI", "current", 4200, False),
            _account("ACC002-SAB", "CUST002", "SAB", "current", 2100, False),
            _account("ACC002-SNB", "CUST002", "SNB", "current", 310, False),
            _account("ACC002-RYD", "CUST002", "RIYAD", "current", 260, False),
        ],
        "loans": [
            {"loan_id": "LN002", "bank_code": "ALINMA", "loan_type": "car", "total": 76800,
             "installment": 1600, "remaining_months": 14, "months_paid": 34, "day": 5},
        ],
        "salary": {"amount": 22000, "day": 25, "bank": "ALINMA", "day_overrides": {},
                   "descs": ["MUDAD PAYROLL MOF ENTITY", "حوالة راتب حكومي"]},
        "recurring": [
            _item("loan_inm", "ALINMA", 5, -1600, ["ALINMA AUTO FIN INSTALLMENT {n2}/48", "قسط تمويل سيارة - الإنماء"], None, None,
                  months_paid=34),
            _item("stc", "ALINMA", 10, -250, ["SADAD BILL - STC"], "STC", "bills", jitter=0.05),
            _item("shahid", "ALINMA", 6, -28, ["SHAHID VIP SUBSCRIPTION"], "Shahid", "subscription"),
            _item("kahraba", "ALINMA", 15, -220, ["SADAD BILL - KAHRABA"], None, "bills", jitter=0.2),
        ],
        "flexible": {
            "groceries": {"monthly": 1400, "count": 5, "bank": "ALINMA",
                          "descs": ["POS DANUBE JEDDAH 12", "POS TAMIMI MARKETS JED"]},
            "cafes": {"monthly": 420, "count": 5, "bank": "ALINMA",
                      "descs": ["POS BREW92 JEDDAH", "مقهى الغيمة - جدة"]},
            "restaurants": {"monthly": 950, "count": 4, "bank": "ALINMA",
                            "descs": ["POS ALROMANSIAH JED", "HUNGERSTATION JEDDAH"]},
            "shopping": {"monthly": 1300, "count": 3, "bank": "ALRAJHI",
                         "descs": ["POS AMAZON.SA RETAIL", "POS RED SEA MALL STORE"]},
            "fuel": {"monthly": 380, "count": 3, "bank": "SAB", "descs": ["POS ALDREES PETROL JED"]},
            "entertainment": {"monthly": 350, "count": 2, "bank": "ALINMA", "descs": ["VOX CINEMAS RED SEA MALL"]},
            "transport": {"monthly": 45, "count": 1, "bank": "SNB", "descs": ["UBER TRIP HELP.UBER.COM"]},
            "misc": {"monthly": 35, "count": 1, "bank": "RIYAD", "descs": ["POS NAHDI PHARMACY JED"]},
        },
        "current_month_pace": {},
    }


def _legacy_khalid_spec() -> dict:
    """Radar customer: host-bank installment on day 27, cafe pace accelerating this month."""
    return {
        "customer": _customer("CUST003", "khalid", "خالد", "Khalid", "1000000003",
                              date(1994, 2, 5), 14500, "Dammam", "Private", "Eastern Services Ltd."),
        "accounts": [
            _account("ACC003-INM", "CUST003", "ALINMA", "current", 4850, True),
            _account("ACC003-SNB", "CUST003", "SNB", "current", 1150, False),
            _account("ACC003-RYD", "CUST003", "RIYAD", "current", 780, False),
            _account("ACC003-RAJ", "CUST003", "ALRAJHI", "current", 160, False),
            _account("ACC003-SAB", "CUST003", "SAB", "current", 90, False),
        ],
        # The radar's day-27 installment sits at the HOST bank so Mode B works
        # right after login, before any linking.
        "loans": [
            {"loan_id": "LN003", "bank_code": "ALINMA", "loan_type": "car", "total": 111600,
             "installment": 3100, "remaining_months": 22, "months_paid": 14, "day": 27},
        ],
        # Salary on day 1: already received this month, so overspending eats real balance.
        "salary": {"amount": 14500, "day": 1, "bank": "ALINMA", "day_overrides": {},
                   "descs": ["MUDAD PAYROLL EASTERN SVCS", "حوالة راتب"]},
        "recurring": [
            _item("rent", "ALINMA", 2, -3800, ["SADAD RENT EJAR PLATFORM", "ايجار شقة - العزيزية"], None, "housing"),
            _item("loan_inm", "ALINMA", 27, -3100, ["ALINMA AUTO FIN INSTALLMENT {n2}/36", "قسط سيارة - الإنماء"], None, None,
                  months_paid=14),
            _item("stc", "ALINMA", 10, -300, ["SADAD BILL - STC"], "STC", "bills", jitter=0.05),
            _item("tabby", "SNB", 21, -220, ["POS TABBY* PAYMENT DMM", "TABBY *{n} OF 4 INSTAL"], None, None,
                  bnpl_total=4, bnpl_paid=1),
        ],
        "flexible": {
            "groceries": {"monthly": 900, "count": 4, "bank": "ALINMA",
                          "descs": ["POS PANDA RETAIL DAMMAM", "POS OTHAIM MRKT DMM"]},
            "cafes": {"monthly": 480, "count": 10, "bank": "ALINMA",
                      "descs": ["POS BARNS COFFEE 1180 DMM", "POS RAVE COFFEE KHOBAR", "مقهى سكرة - الدمام"]},
            "restaurants": {"monthly": 750, "count": 5, "bank": "ALINMA",
                            "descs": ["POS HERFY KHOBAR", "JAHEZ ORDER DAMMAM", "POS MAESTRO PIZZA"]},
            "entertainment": {"monthly": 250, "count": 2, "bank": "ALINMA", "descs": ["POS PLAYSTATION NETWORK"]},
            "fuel": {"monthly": 420, "count": 4, "bank": "SNB", "descs": ["POS SASCO FUEL DMM"]},
            "shopping": {"monthly": 180, "count": 2, "bank": "RIYAD", "descs": ["POS AMAZON.SA RETAIL"]},
            "transport": {"monthly": 40, "count": 1, "bank": "ALRAJHI", "descs": ["UBER TRIP HELP.UBER.COM"]},
            "misc": {"monthly": 30, "count": 1, "bank": "SAB", "descs": ["POS NAHDI PHARMACY DMM"]},
        },
        # Current-month acceleration: cafes more than doubled, restaurants slightly up.
        # This is what the radar's pace math must catch.
        "current_month_pace": {"cafes": 2.2, "restaurants": 1.15},
        # The generator derives the host balance so the projected gap before the
        # day-27 installment lands near this value whatever day the data is seeded.
        "radar_gap_target": 340,
    }


def _legacy_noura_spec() -> dict:
    """Overstretched customer: loan + three BNPL stacks across SNB/Al Rajhi — the avoid case."""
    return {
        "customer": _customer("CUST004", "noura", "نورة", "Noura", "1000000004",
                              date(1997, 8, 30), 9500, "Riyadh", "Private", "Retail Group Co."),
        "accounts": [
            _account("ACC004-INM", "CUST004", "ALINMA", "current", 2100, True),
            _account("ACC004-SNB", "CUST004", "SNB", "current", 600, False),
            _account("ACC004-RAJ", "CUST004", "ALRAJHI", "current", 350, False),
            _account("ACC004-RYD", "CUST004", "RIYAD", "current", 120, False),
            _account("ACC004-SAB", "CUST004", "SAB", "current", 80, False),
        ],
        "loans": [
            {"loan_id": "LN004", "bank_code": "SNB", "loan_type": "personal", "total": 68400,
             "installment": 1900, "remaining_months": 18, "months_paid": 18, "day": 5},
        ],
        "salary": {"amount": 9500, "day": 25, "bank": "ALINMA", "day_overrides": {},
                   "descs": ["MUDAD PAYROLL RETAIL GROUP", "حوالة راتب"]},
        "recurring": [
            _item("rent", "ALINMA", 3, -3500, ["SADAD RENT EJAR PLATFORM", "ايجار استوديو - النرجس"], None, "housing"),
            _item("stc", "ALINMA", 10, -250, ["SADAD BILL - STC"], "STC", "bills", jitter=0.05),
            _item("loan_snb", "SNB", 5, -1900, ["SNB PERSONAL FIN INSTALLMENT {n2}/36"], None, None, months_paid=18),
            _item("tabby1", "SNB", 9, -350, ["POS TABBY* PAYMENT RUH", "TABBY *{n} OF 6 INSTAL"], None, None,
                  bnpl_total=6, bnpl_paid=2),
            _item("tabby2", "SNB", 19, -190, ["TABBY *{n} OF 4 INSTAL", "POS TABBY PAYMENT"], None, None,
                  bnpl_total=4, bnpl_paid=2),
            _item("jamiya", "ALRAJHI", 7, -500, ["حوالة - جمعية زميلات العمل"], None, None),
            _item("tamara", "ALRAJHI", 14, -280, ["تمارا - قسط {n} من 4"], None, None,
                  bnpl_total=4, bnpl_paid=1),
        ],
        "flexible": {
            "groceries": {"monthly": 700, "count": 4, "bank": "ALINMA", "descs": ["POS PANDA RETAIL RIYADH"]},
            "cafes": {"monthly": 380, "count": 6, "bank": "ALINMA",
                      "descs": ["POS HALF MILLION RUH", "مقهى نص مليون"]},
            "restaurants": {"monthly": 600, "count": 4, "bank": "SNB", "descs": ["HUNGERSTATION RIYADH"]},
            "shopping": {"monthly": 520, "count": 3, "bank": "ALRAJHI",
                         "descs": ["POS SHEIN.COM", "POS NAMSHI GENERAL TRADING"]},
            "transport": {"monthly": 50, "count": 1, "bank": "RIYAD", "descs": ["UBER TRIP HELP.UBER.COM"]},
            "misc": {"monthly": 25, "count": 1, "bank": "SAB", "descs": ["POS NAHDI PHARMACY 411"]},
        },
        # The OVERSPEND radar case: no installment fails, but cafes + groceries are
        # running hot enough that the spendable balance dips below zero before her
        # day-25 salary — the radar should say what to cut to make it through.
        "current_month_pace": {"cafes": 2.4, "groceries": 1.7},
        "radar_trough_target": 260,
    }


def _sara_spec() -> dict:
    """Disciplined government professional with a strong emergency fund."""
    return {
        "customer": _customer("CUST002", "sara", "\u0633\u0627\u0631\u0629", "Sara", "1000000002",
                              date(1988, 11, 20), 22000, "Jeddah", "Government", "Ministry Entity"),
        "accounts": [
            _account("ACC002-INM", "CUST002", "ALINMA", "current", 31000, True),
            _account("ACC002-INMS", "CUST002", "ALINMA", "savings", 45000, False),
            _account("ACC002-RAJ", "CUST002", "ALRAJHI", "current", 5500, False),
            _account("ACC002-RAJS", "CUST002", "ALRAJHI", "savings", 18000, False),
        ],
        "loans": [
            {"loan_id": "LN002", "bank_code": "ALINMA", "loan_type": "car", "total": 76800,
             "installment": 1600, "remaining_months": 14, "months_paid": 34, "day": 5},
        ],
        "salary": {"amount": 22000, "day": 27, "bank": "ALINMA", "day_overrides": {2: 26},
                   "descs": ["MUDAD PAYROLL MINISTRY ENTITY", "GOVERNMENT SALARY TRANSFER"]},
        "recurring": [
            _item("rent", "ALINMA", 2, -4500, ["SADAD RENT EJAR PLATFORM", "EJAR APARTMENT JEDDAH"], None, "housing"),
            _item("loan_inm", "ALINMA", 5, -1600, ["ALINMA AUTO FIN INSTALLMENT {n2}/48"], None, None,
                  months_paid=34),
            _item("stc", "ALINMA", 10, -260, ["SADAD BILL - STC"], "STC", "bills", jitter=0.05),
            _item("shahid", "ALINMA", 6, -29, ["SHAHID VIP SUBSCRIPTION"], "Shahid", "subscription"),
            _item("electricity", "ALINMA", 15, -280, ["SADAD BILL - SAUDI ELECTRICITY"], None, "bills", jitter=0.2),
            _item("internet", "ALINMA", 12, -250, ["SADAD BILL - MOBILY FIBER"], "Mobily", "bills", jitter=0.03),
            _item("gym", "ALRAJHI", 7, -199, ["PUREGYM MONTHLY MEMBERSHIP"], "PureGym", "subscription"),
        ],
        "flexible": {
            "groceries": {"monthly": 1500, "count": 6, "bank": "ALINMA",
                          "descs": ["POS DANUBE JEDDAH 12", "POS TAMIMI MARKETS JED"]},
            "cafes": {"monthly": 350, "count": 5, "bank": "ALINMA",
                      "descs": ["POS BREW92 JEDDAH", "POS MEDD CAFE JEDDAH"]},
            "restaurants": {"monthly": 800, "count": 4, "bank": "ALINMA",
                            "descs": ["POS ALROMANSIAH JED", "HUNGERSTATION JEDDAH"]},
            "shopping": {"monthly": 900, "count": 3, "bank": "ALRAJHI",
                         "descs": ["POS AMAZON.SA RETAIL", "POS RED SEA MALL STORE"]},
            "fuel": {"monthly": 500, "count": 4, "bank": "ALINMA", "descs": ["POS ALDREES PETROL JED"]},
            "entertainment": {"monthly": 350, "count": 2, "bank": "ALINMA", "descs": ["VOX CINEMAS RED SEA MALL"]},
            "transport": {"monthly": 150, "count": 3, "bank": "ALRAJHI", "descs": ["UBER TRIP HELP.UBER.COM"]},
            "healthcare": {"monthly": 300, "count": 2, "bank": "ALINMA",
                           "descs": ["POS NAHDI PHARMACY JED", "POS SULAIMAN FAQEEH COPAY"]},
        },
        "events": [
            _event(-6, 27, 7000, "ALINMA", "ANNUAL GOVERNMENT PERFORMANCE BONUS", "Employer"),
            _event(-4, 18, -4800, "ALRAJHI", "FLYNAS HOLIDAY PACKAGE JED DXB", "Flynas"),
            _event(-2, 11, -1800, "ALINMA", "POS DENTAL CLINIC JEDDAH", "Dental Clinic"),
            _event(-1, 14, 420, "ALRAJHI", "REFUND AMAZON.SA ORDER", "Amazon.sa"),
        ],
        "current_month_pace": {},
    }


def _khalid_spec() -> dict:
    """Young professional whose cafe and restaurant spending is accelerating."""
    return {
        "customer": _customer("CUST003", "khalid", "\u062e\u0627\u0644\u062f", "Khalid", "1000000003",
                              date(1994, 2, 5), 14500, "Dammam", "Private", "Eastern Services Ltd."),
        "accounts": [
            _account("ACC003-INM", "CUST003", "ALINMA", "current", 4850, True),
            _account("ACC003-INMS", "CUST003", "ALINMA", "savings", 2500, False),
            _account("ACC003-RAJ", "CUST003", "ALRAJHI", "current", 1650, False),
        ],
        "loans": [
            {"loan_id": "LN003", "bank_code": "ALINMA", "loan_type": "car", "total": 111600,
             "installment": 3100, "remaining_months": 22, "months_paid": 14, "day": 27},
        ],
        "salary": {"amount": 14500, "day": 1, "bank": "ALINMA", "day_overrides": {},
                   "descs": ["MUDAD PAYROLL EASTERN SERVICES", "SALARY TRANSFER EASTERN SVCS"]},
        "recurring": [
            _item("rent", "ALINMA", 2, -3800, ["SADAD RENT EJAR PLATFORM", "EJAR APARTMENT DAMMAM"], None, "housing"),
            _item("loan_inm", "ALINMA", 27, -3100, ["ALINMA AUTO FIN INSTALLMENT {n2}/36"], None, None,
                  months_paid=14),
            _item("stc", "ALINMA", 10, -300, ["SADAD BILL - STC"], "STC", "bills", jitter=0.05),
            _item("internet", "ALINMA", 12, -220, ["SADAD BILL - SALAM INTERNET"], "Salam", "bills", jitter=0.03),
            _item("gym", "ALINMA", 8, -180, ["BODY MASTERS MONTHLY MEMBERSHIP"], "Body Masters", "subscription"),
            _item("tabby", "ALRAJHI", 21, -220, ["TABBY *{n} OF 4 INSTAL", "POS TABBY PAYMENT DMM"], None, None,
                  bnpl_total=4, bnpl_paid=1),
        ],
        "flexible": {
            "groceries": {"monthly": 1000, "count": 5, "bank": "ALINMA", "descs": ["POS PANDA RETAIL DAMMAM", "POS OTHAIM DMM"]},
            "cafes": {"monthly": 520, "count": 10, "bank": "ALINMA", "descs": ["POS BARNS COFFEE DMM", "POS RATIO CAFE KHOBAR"]},
            "restaurants": {"monthly": 780, "count": 5, "bank": "ALINMA", "descs": ["JAHEZ ORDER DAMMAM", "POS MAESTRO PIZZA"]},
            "entertainment": {"monthly": 280, "count": 2, "bank": "ALINMA", "descs": ["PLAYSTATION NETWORK", "VOX CINEMAS DHAHRAN"]},
            "fuel": {"monthly": 450, "count": 4, "bank": "ALRAJHI", "descs": ["POS SASCO FUEL DMM"]},
            "shopping": {"monthly": 300, "count": 2, "bank": "ALRAJHI", "descs": ["POS AMAZON.SA RETAIL"]},
            "transport": {"monthly": 150, "count": 3, "bank": "ALINMA", "descs": ["UBER TRIP HELP.UBER.COM"]},
            "healthcare": {"monthly": 120, "count": 1, "bank": "ALINMA", "descs": ["POS NAHDI PHARMACY DMM"]},
        },
        "events": [
            _event(-5, 16, -2300, "ALRAJHI", "POS JARIR BOOKSTORE LAPTOP ACCESSORY", "Jarir"),
            _event(-2, 20, -1600, "ALRAJHI", "POS PETROMIN CAR REPAIR KHOBAR", "Petromin"),
            _event(-1, 23, 600, "ALINMA", "EMPLOYEE EXPENSE REIMBURSEMENT", "Employer"),
        ],
        "current_month_pace": {"cafes": 2.2, "restaurants": 1.3},
        "radar_gap_target": 340,
    }


def _noura_spec() -> dict:
    """Lower-income renter with overlapping debt and limited cash reserves."""
    return {
        "customer": _customer("CUST004", "noura", "\u0646\u0648\u0631\u0629", "Noura", "1000000004",
                              date(1997, 8, 30), 10200, "Riyadh", "Private", "Retail Group Co."),
        "accounts": [
            _account("ACC004-INM", "CUST004", "ALINMA", "current", 2100, True),
            _account("ACC004-INMS", "CUST004", "ALINMA", "savings", 700, False),
            _account("ACC004-RAJ", "CUST004", "ALRAJHI", "current", 450, False),
        ],
        "loans": [
            {"loan_id": "LN004", "bank_code": "ALRAJHI", "loan_type": "personal", "total": 68400,
             "installment": 1900, "remaining_months": 18, "months_paid": 18, "day": 5},
        ],
        "salary": {"amount": 10200, "day": 25, "bank": "ALINMA", "day_overrides": {},
                   "descs": ["MUDAD PAYROLL RETAIL GROUP", "SALARY TRANSFER RETAIL GROUP"]},
        "recurring": [
            _item("rent", "ALINMA", 3, -2900, ["SADAD RENT EJAR PLATFORM", "EJAR SHARED APARTMENT RIYADH"], None, "housing"),
            _item("stc", "ALINMA", 10, -230, ["SADAD BILL - STC"], "STC", "bills", jitter=0.05),
            _item("electricity", "ALINMA", 13, -180, ["SADAD BILL - SAUDI ELECTRICITY"], None, "bills", jitter=0.2),
            _item("internet", "ALINMA", 12, -180, ["SADAD BILL - MOBILY HOME"], "Mobily", "bills", jitter=0.04),
            _item("loan_raj", "ALRAJHI", 5, -1900, ["ARB PERSONAL FIN INSTALLMENT {n2}/36"], None, None, months_paid=18),
            _item("tabby1", "ALRAJHI", 9, -350, ["TABBY *{n} OF 6 INSTAL", "POS TABBY PAYMENT"], None, None, bnpl_total=6, bnpl_paid=2),
            _item("tabby2", "ALRAJHI", 19, -190, ["TABBY *{n} OF 4 INSTAL"], None, None, bnpl_total=4, bnpl_paid=2),
            _item("jamiya", "ALRAJHI", 7, -500, ["MONTHLY JAMIYA TRANSFER TO COLLEAGUES"], None, None),
            _item("tamara", "ALRAJHI", 14, -280, ["TAMARA INSTALMENT {n} OF 4"], None, None, bnpl_total=4, bnpl_paid=1),
        ],
        "flexible": {
            "groceries": {"monthly": 850, "count": 5, "bank": "ALINMA", "descs": ["POS PANDA RETAIL RIYADH", "POS OTHAIM MARKET"]},
            "cafes": {"monthly": 320, "count": 6, "bank": "ALINMA", "descs": ["POS HALF MILLION RUH", "POS BARN'S COFFEE"]},
            "restaurants": {"monthly": 500, "count": 4, "bank": "ALINMA", "descs": ["HUNGERSTATION RIYADH", "POS ALBAIK"]},
            "shopping": {"monthly": 420, "count": 3, "bank": "ALRAJHI", "descs": ["POS SHEIN.COM", "POS NAMSHI"]},
            "transport": {"monthly": 250, "count": 5, "bank": "ALRAJHI", "descs": ["UBER TRIP HELP.UBER.COM", "POS CAREEM RIDE"]},
            "healthcare": {"monthly": 120, "count": 1, "bank": "ALINMA", "descs": ["POS NAHDI PHARMACY"]},
        },
        "events": [
            _event(-4, 19, -500, "ALRAJHI", "ATM CASH WITHDRAWAL RIYADH", "ATM"),
            _event(-3, 8, -900, "ALINMA", "POS DALLAH HOSPITAL COPAY", "Dallah Hospital"),
            _event(-2, 25, 650, "ALINMA", "OVERTIME PAYMENT RETAIL GROUP", "Employer"),
            _event(-1, 21, -1100, "ALRAJHI", "POS EXTRA STORES WASHING MACHINE", "eXtra"),
        ],
        "current_month_pace": {"cafes": 2.0, "groceries": 1.5},
        "radar_trough_target": 260,
    }


def _abdullah_spec() -> dict:
    """Established family household with strong assets but high fixed commitments."""
    return {
        "customer": _customer("CUST005", "abdullah", "\u0639\u0628\u062f\u0627\u0644\u0644\u0647", "Abdullah", "1000000005",
                              date(1985, 6, 18), 26000, "Riyadh", "Private", "Saudi Telecom Company"),
        "accounts": [
            _account("ACC005-INM", "CUST005", "ALINMA", "current", 38000, True),
            _account("ACC005-INMS", "CUST005", "ALINMA", "savings", 55000, False),
            _account("ACC005-RAJ", "CUST005", "ALRAJHI", "current", 12000, False),
            _account("ACC005-RAJS", "CUST005", "ALRAJHI", "savings", 25000, False),
        ],
        "loans": [
            {"loan_id": "LN005-HOME", "bank_code": "ALINMA", "loan_type": "home", "total": 624000,
             "installment": 5200, "remaining_months": 96, "months_paid": 24, "day": 1},
            {"loan_id": "LN005-CAR", "bank_code": "ALRAJHI", "loan_type": "car", "total": 72000,
             "installment": 2400, "remaining_months": 10, "months_paid": 20, "day": 8},
        ],
        "salary": {"amount": 26000, "day": 27, "bank": "ALINMA", "day_overrides": {},
                   "descs": ["MUDAD PAYROLL SAUDI TELECOM COMPANY", "SALARY TRANSFER STC"]},
        "recurring": [
            _item("home_loan", "ALINMA", 1, -5200, ["ALINMA HOME FINANCE INSTALLMENT {n2}/120"], None, None, months_paid=24),
            _item("car_loan", "ALRAJHI", 8, -2400, ["ARB AUTO FINANCE INSTALLMENT {n2}/30"], None, None, months_paid=20),
            _item("parents", "ALRAJHI", 26, -1200, ["MONTHLY TRANSFER TO PARENTS", "FAMILY SUPPORT TRANSFER"], None, "transfer"),
            _item("nursery", "ALINMA", 4, -1800, ["SADAD LITTLE SCHOLARS NURSERY", "MONTHLY NURSERY FEES"], "Little Scholars", "education"),
            _item("electricity", "ALINMA", 15, -650, ["SADAD BILL - SAUDI ELECTRICITY"], None, "bills", jitter=0.22),
            _item("stc", "ALINMA", 10, -420, ["SADAD BILL - STC FAMILY PLAN"], "STC", "bills", jitter=0.04),
            _item("internet", "ALINMA", 12, -300, ["SADAD BILL - STC FIBER"], "STC", "bills", jitter=0.03),
            _item("water", "ALINMA", 16, -120, ["SADAD BILL - NATIONAL WATER COMPANY"], None, "bills", jitter=0.2),
            _item("netflix", "ALRAJHI", 9, -65, ["NETFLIX.COM AMSTERDAM NL"], "Netflix", "subscription"),
            _item("jamiya", "ALRAJHI", 15, -1000, ["MONTHLY JAMIYA FAMILY TRANSFER"], None, None),
        ],
        "flexible": {
            "groceries": {"monthly": 2200, "count": 8, "bank": "ALINMA", "descs": ["POS TAMIMI MARKETS RIYADH", "POS DANUBE HITTIN"]},
            "cafes": {"monthly": 350, "count": 5, "bank": "ALINMA", "descs": ["POS DR CAFE RIYADH", "POS HALF MILLION"]},
            "restaurants": {"monthly": 1100, "count": 5, "bank": "ALINMA", "descs": ["HUNGERSTATION FAMILY ORDER", "POS ALROMANSIAH"]},
            "fuel": {"monthly": 650, "count": 5, "bank": "ALRAJHI", "descs": ["POS ALDREES PETROL RIYADH"]},
            "shopping": {"monthly": 900, "count": 3, "bank": "ALRAJHI", "descs": ["POS AMAZON.SA RETAIL", "POS CENTREPOINT RIYADH"]},
            "entertainment": {"monthly": 400, "count": 2, "bank": "ALINMA", "descs": ["VOX CINEMAS FAMILY TICKETS", "POS BOULEVARD WORLD"]},
            "healthcare": {"monthly": 300, "count": 2, "bank": "ALINMA", "descs": ["POS NAHDI PHARMACY", "POS ALHABIB COPAY"]},
            "transport": {"monthly": 100, "count": 2, "bank": "ALRAJHI", "descs": ["UBER TRIP HELP.UBER.COM"]},
        },
        "events": [
            _event(-6, 27, 12000, "ALINMA", "ANNUAL PERFORMANCE BONUS STC", "Employer"),
            _event(-5, 20, -8500, "ALRAJHI", "SAUDIA FAMILY HOLIDAY BOOKING", "Saudia"),
            _event(-2, 18, -2400, "ALINMA", "POS HOME MAINTENANCE SERVICES", "Home Services"),
            _event(-1, 6, -1800, "ALRAJHI", "TAWUNIYA ANNUAL MOTOR INSURANCE", "Tawuniya"),
        ],
        "current_month_pace": {},
    }


def _customer(customer_id: str, username: str, ar_name: str, en_name: str, national_id: str,
              birthday: date, salary: float, city: str, sector: str, employer: str) -> dict:
    """Build one customers-table row."""
    return {
        "customer_id": customer_id,
        "username_en": username,
        "ar_name": ar_name,
        "en_name": en_name,
        "national_id": national_id,
        "birthday": birthday.isoformat(),
        "salary": salary,
        "city": city,
        "employment_sector": sector,
        "employer_name": employer,
        "account_open_date": date(2019, 1, 15).isoformat(),
        "created_at": _now(),
    }


def _account(account_id: str, customer_id: str, bank_code: str, account_type: str,
             balance: float, is_primary: bool) -> dict:
    """Build one accounts-table row with a fake but well-formed SA IBAN."""
    digest = hashlib.sha256(account_id.encode("utf-8")).digest()
    digits = f"{int.from_bytes(digest[:8], 'big') % 10**18:018d}"
    return {
        "account_id": account_id,
        "customer_id": customer_id,
        "bank_code": bank_code,
        "bank_name_ar": BANKS[bank_code],
        "account_type": account_type,
        "iban": f"SA44{digits[:2]}{digits[2:]}",
        "balance": balance,
        "is_primary": is_primary,
        "created_at": _now(),
    }


def _item(key: str, bank: str, day: int, amount: float, descs: list[str],
          merchant: str | None, category: str | None, jitter: float = 0.0,
          months_paid: int | None = None, bnpl_total: int | None = None,
          bnpl_paid: int | None = None) -> dict:
    """Build one recurring-item spec used by the transaction renderer."""
    return {
        "key": key, "bank": bank, "day": day, "amount": amount, "descs": descs,
        "merchant": merchant, "category": category, "jitter": jitter,
        "months_paid": months_paid, "bnpl_total": bnpl_total, "bnpl_paid": bnpl_paid,
    }


def _event(month_offset: int, day: int, amount: float, bank: str, desc: str,
           merchant: str | None = None) -> dict:
    """Build a one-off life event such as a bonus, repair, trip, or refund."""
    return {
        "month_offset": month_offset,
        "day": day,
        "amount": amount,
        "bank": bank,
        "desc": desc,
        "merchant": merchant,
    }


def _tune_radar_balance(spec: dict, today: date, rows: list[dict]) -> None:
    """Derive the radar customer's host balance so the demo gap is stable.

    Uses HOST-bank items only, because the radar must fire before any external
    bank is linked. Post-linking, external installments only widen the gap.
    Seeding on/after the installment day leaves the balance as-is (belt-secure demo).
    """
    target = spec.get("radar_gap_target")
    if not target:
        return
    host = next(a["bank_code"] for a in spec["accounts"] if a["is_primary"])
    loan = next(l for l in spec["loans"] if l["bank_code"] == host)
    if today.day >= loan["day"]:
        return
    current_month = today.isoformat()[:7]
    mtd_flexible = sum(
        abs(row["amount"]) for row in rows
        if row.get("_flex") and row["bank_code"] == host
        and str(row["transaction_date"]).startswith(current_month)
    )
    pace = mtd_flexible / today.day if today.day >= 3 and mtd_flexible else sum(
        plan["monthly"] * spec["current_month_pace"].get(category, 1.0)
        for category, plan in spec["flexible"].items() if plan["bank"] == host
    ) / 30
    upcoming = sum(
        -item["amount"] for item in spec["recurring"]
        if item["bank"] == host and today.day < item["day"] < loan["day"] and _item_active(item, 0)
    )
    needed = loan["installment"] - target + pace * (loan["day"] - today.day) + upcoming
    primary = next(a for a in spec["accounts"] if a["is_primary"])
    others = sum(a["balance"] for a in spec["accounts"]
                 if not a["is_primary"] and a["bank_code"] == host
                 and a["account_type"] != "savings")
    primary["balance"] = max(round(needed - others), 500)


def _tune_trough_balance(spec: dict, today: date, rows: list[dict]) -> None:
    """Derive the overspend customer's host balance so the pre-salary dip is stable.

    Sets the spendable balance so that, at the measured spending pace, the balance
    crosses about -target shortly before salary day — the radar's overspend case.
    Seeding on/after salary day leaves the balance as-is (on-track demo instead).
    """
    target = spec.get("radar_trough_target")
    if not target:
        return
    host = next(a["bank_code"] for a in spec["accounts"] if a["is_primary"])
    salary_day = spec["salary"]["day"]
    if today.day >= salary_day:
        return
    current_month = today.isoformat()[:7]
    mtd_flexible = sum(
        abs(row["amount"]) for row in rows
        if row.get("_flex") and row["bank_code"] == host
        and str(row["transaction_date"]).startswith(current_month)
    )
    pace = mtd_flexible / today.day if today.day >= 3 and mtd_flexible else sum(
        plan["monthly"] * spec["current_month_pace"].get(category, 1.0)
        for category, plan in spec["flexible"].items() if plan["bank"] == host
    ) / 30
    upcoming = sum(
        -item["amount"] for item in spec["recurring"]
        if item["bank"] == host and today.day < item["day"] < salary_day and _item_active(item, 0)
    )
    needed = pace * (salary_day - today.day) + upcoming - target
    primary = next(a for a in spec["accounts"] if a["is_primary"])
    others = sum(a["balance"] for a in spec["accounts"]
                 if not a["is_primary"] and a["bank_code"] == host
                 and a["account_type"] != "savings")
    primary["balance"] = max(round(needed - others), 100)


def _render_loans(spec: dict, today: date) -> list[dict]:
    """Build loans-table rows with dates derived from months_paid relative to today."""
    rows = []
    for loan in spec["loans"]:
        first = _shift_month(today, -loan["months_paid"], loan["day"])
        end = _shift_month(today, loan["remaining_months"], loan["day"])
        total_months = loan["months_paid"] + loan["remaining_months"]
        rows.append({
            "loan_id": loan["loan_id"],
            "customer_id": spec["customer"]["customer_id"],
            "bank_code": loan["bank_code"],
            "loan_type": loan["loan_type"],
            "loan_total_amount": round(loan["total"] * 0.88),
            "total_profit_amount": round(loan["total"] * 0.12),
            "total_amount": loan["total"],
            "remaining_amount": loan["installment"] * loan["remaining_months"],
            "monthly_installment": loan["installment"],
            "remaining_months": loan["remaining_months"],
            "first_installment_date": first.isoformat(),
            "start_date": first.isoformat(),
            "end_date": end.isoformat(),
            "status": "active",
            "created_at": _now(),
        })
        if total_months <= 0:
            raise ValueError(f"Loan {loan['loan_id']} has no installments at all.")
    return rows


def _render_transactions(spec: dict, today: date, rng: random.Random) -> list[dict]:
    """Render salary, recurring items, and flexible spending into transaction rows."""
    rows: list[dict] = []
    for months_back in range(HISTORY_MONTHS, 0, -1):
        rows.extend(_month_rows(spec, today, -months_back, rng, cutoff_day=None))
    rows.extend(_month_rows(spec, today, 0, rng, cutoff_day=today.day))
    for index, row in enumerate(rows):
        row["transaction_id"] = f"TX-{spec['customer']['customer_id']}-{index:05d}"
    return rows


def _month_rows(spec: dict, today: date, month_offset: int, rng: random.Random,
                cutoff_day: int | None) -> list[dict]:
    """Render one calendar month of transactions; cutoff_day limits the current month."""
    rows = []
    salary = spec["salary"]
    salary_day = salary["day_overrides"].get(-month_offset, salary["day"])
    if cutoff_day is None or salary_day <= cutoff_day:
        rows.append(_txn(spec, salary["bank"], _shift_month(today, month_offset, salary_day),
                         salary["amount"], rng.choice(salary["descs"]), "Employer", "salary", "income"))

    for item in spec["recurring"]:
        if not _item_active(item, month_offset):
            continue
        if cutoff_day is not None and item["day"] > cutoff_day:
            continue
        amount = item["amount"] * (1 + rng.uniform(-item["jitter"], item["jitter"]))
        desc = _item_desc(item, month_offset, rng)
        rows.append(_txn(spec, item["bank"], _shift_month(today, month_offset, item["day"]),
                         round(amount), desc, item["merchant"], item["category"], "expense"))

    for event in spec.get("events", []):
        if event["month_offset"] != month_offset:
            continue
        if cutoff_day is not None and event["day"] > cutoff_day:
            continue
        txn_type = "income" if event["amount"] > 0 else "expense"
        rows.append(_txn(spec, event["bank"], _shift_month(today, month_offset, event["day"]),
                         event["amount"], event["desc"], event["merchant"], None, txn_type))

    rows.extend(_flexible_rows(spec, today, month_offset, rng, cutoff_day))
    return rows


def _item_active(item: dict, month_offset: int) -> bool:
    """Decide if a recurring item pays in this month (BNPL plans have limited life)."""
    if item["bnpl_total"] is None:
        return True
    # BNPL: bnpl_paid installments happened in past months; the plan started then.
    installment_number = item["bnpl_paid"] + month_offset + 1
    return 1 <= installment_number <= item["bnpl_total"]


def _item_desc(item: dict, month_offset: int, rng: random.Random) -> str:
    """Pick a description variant and fill installment counters when present."""
    desc = rng.choice(item["descs"])
    if "{n}" in desc and item["bnpl_paid"] is not None:
        desc = desc.replace("{n}", str(item["bnpl_paid"] + month_offset + 1))
    if "{n2}" in desc and item["months_paid"] is not None:
        desc = desc.replace("{n2}", str(item["months_paid"] + month_offset + 1))
    if "{hijri}" in desc:
        desc = desc.replace("{hijri}", rng.choice(["رجب", "شعبان", "رمضان", "شوال"]))
    return desc


def _flexible_rows(spec: dict, today: date, month_offset: int, rng: random.Random,
                   cutoff_day: int | None) -> list[dict]:
    """Render flexible-category spending; the current month respects pace multipliers."""
    rows = []
    for category, plan in spec["flexible"].items():
        pace = spec["current_month_pace"].get(category, 1.0) if cutoff_day is not None else 1.0
        month_total = plan["monthly"] * (1 + rng.uniform(-0.12, 0.12)) * pace
        if cutoff_day is not None:
            month_total *= cutoff_day / 30
        count = max(1, round(plan["count"] * (cutoff_day / 30))) if cutoff_day else plan["count"]
        last_day = cutoff_day or 28
        # Preserve purchase-size variety while keeping the category total equal
        # to the intended monthly budget. The previous independent multipliers
        # accidentally inflated some customers' spending by 30-60 percent.
        weights = [rng.uniform(0.35, 2.3) for _ in range(count)]
        target = max(1, round(month_total))
        amounts = [max(1, round(target * weight / sum(weights))) for weight in weights]
        amounts[-1] += target - sum(amounts)
        for amount in amounts:
            day = rng.randint(1, last_day)
            row = _txn(spec, plan["bank"], _shift_month(today, month_offset, day),
                       -amount, rng.choice(plan["descs"]),
                       None, category, "expense")
            row["_flex"] = True  # internal tag for balance tuning; stripped before load
            rows.append(row)
    return rows


def _txn(spec: dict, bank: str, txn_date: date, amount: float, desc: str,
         merchant: str | None, category: str | None, txn_type: str) -> dict:
    """Build one transactions-table row tied to the right cross-bank account."""
    account = next(
        (a for a in spec["accounts"] if a["bank_code"] == bank and a["account_type"] == "current"),
        spec["accounts"][0],
    )
    return {
        "transaction_id": "",  # filled by the renderer with a stable sequence
        "customer_id": spec["customer"]["customer_id"],
        "account_id": account["account_id"],
        "bank_code": bank,
        "transaction_date": txn_date.isoformat(),
        "merchant": merchant,
        "raw_description": desc,
        "amount": float(amount),
        "transaction_type": txn_type,
        "channel": _infer_channel(desc, txn_type),
        "created_at": _now(),
    }


def _infer_channel(desc: str, txn_type: str) -> str:
    """Infer a plausible raw banking channel without relying on a category field."""
    upper = desc.upper()
    if txn_type == "income" or any(token in upper for token in ("TRANSFER", "TRF", "PAYROLL", "BONUS", "REIMBURSEMENT", "REFUND")):
        return "transfer"
    if "SADAD" in upper or "EJAR" in upper:
        return "sadad"
    if "ATM" in upper or "CASH WITHDRAWAL" in upper:
        return "atm"
    if any(token in upper for token in ("HUNGERSTATION", "JAHEZ", "AMAZON", "SHEIN", "NAMSHI", "NETFLIX", "SHAHID", "TABBY", "TAMARA", "PLAYSTATION")):
        return "ecommerce"
    if upper.startswith("POS"):
        return "pos"
    return "card"


def _shift_month(today: date, month_offset: int, day: int) -> date:
    """Return the given day in the month offset from today, clamped to month length."""
    total = today.year * 12 + (today.month - 1) + month_offset
    year, month = divmod(total, 12)
    month += 1
    return date(year, month, min(day, monthrange(year, month)[1]))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
