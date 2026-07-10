"""Generate synthetic cross-bank demo data with realistically messy transaction descriptions."""
import random
from calendar import monthrange
from datetime import date, datetime, timezone


# All seed dates are RELATIVE to the run date so the radar demo works whenever
# the data is loaded. Six full months of history plus the current month-to-date.
HISTORY_MONTHS = 6

BANKS = {
    "ALRAJHI": "مصرف الراجحي",
    "SNB": "البنك الأهلي السعودي",
    "RIYAD": "بنك الرياض",
    "SAB": "البنك السعودي الأول",
}


def generate_all(today: date | None = None) -> dict[str, list[dict]]:
    """Build every seed table as plain row dicts keyed by table name."""
    today = today or date.today()
    rng = random.Random(4471)
    specs = [_fahad_spec(), _sara_spec(), _khalid_spec(), _noura_spec()]

    customers, accounts, loans, transactions = [], [], [], []
    for spec in specs:
        rows = _render_transactions(spec, today, rng)
        _tune_radar_balance(spec, today, rows)
        for row in rows:
            row.pop("_flex", None)
        customers.append(spec["customer"])
        accounts.extend(spec["accounts"])
        loans.extend(_render_loans(spec, today))
        transactions.extend(rows)
    return {
        "customers": customers,
        "accounts": accounts,
        "loans": loans,
        "transactions": transactions,
    }


def _fahad_spec() -> dict:
    """Demo hero: healthy at his primary bank, stretched across the other banks."""
    return {
        "customer": _customer("CUST001", "fahad", "فهد ", "Fahad Alotaibi", "1000000001",
                              date(1990, 4, 12), 16500, "Riyadh", "Private", "Najd Logistics Co."),
        "accounts": [
            _account("ACC001-RAJ", "CUST001", "ALRAJHI", "current", 22400, True),
            _account("ACC001-RAJS", "CUST001", "ALRAJHI", "savings", 8100, False),
            _account("ACC001-SNB", "CUST001", "SNB", "current", 3850, False),
            _account("ACC001-RYD", "CUST001", "RIYAD", "current", 2300, False),
        ],
        # Personal loan at ANOTHER bank with 2 installments left: the forecast must
        # drop it from month 3 — the one-time DBR check at his primary bank never sees it.
        "loans": [
            {"loan_id": "LN001", "bank_code": "SNB", "loan_type": "personal", "total": 79200,
             "installment": 2200, "remaining_months": 2, "months_paid": 34, "day": 27},
        ],
        "salary": {"amount": 16500, "day": 25, "bank": "ALRAJHI",
                   # Two late months in history: the salary-timing variance signal.
                   "day_overrides": {3: 29, 5: 28},
                   "descs": ["MUDAD PAYROLL NAJD LOGISTICS", "حوالة راتب - مداد", "SALARY TRF NAJD LOG CO"]},
        "recurring": [
            _item("rent", "ALRAJHI", 3, -4500, ["SADAD RENT EJAR PLATFORM", "ايجار - منصة إيجار"], None, "housing"),
            _item("jamiya", "RIYAD", 5, -1000, ["حوالة داخلية - جمعية شهر {hijri}", "حوالة - جمعية الحي"], None, None),
            _item("family", "ALRAJHI", 26, -1500, ["TRF TO ABU FAHAD 0501XXXXXX", "حوالة الى ابو فهد"], None, "transfer"),
            _item("loan_snb", "SNB", 27, -2200, ["SNB PERSONAL FIN INSTALLMENT {n2}/36", "قسط تمويل شخصي - الاهلي"], None, None,
                  months_paid=34),
            _item("tabby1", "SNB", 12, -450, ["POS TABBY* PAYMENT RUH", "TABBY *INSTALMENT {n} OF 4"], None, None,
                  bnpl_total=4, bnpl_paid=2),
            _item("tamara", "RIYAD", 18, -380, ["تمارا - قسط {n} من 4", "TAMARA PAYMENT RYD"], None, None,
                  bnpl_total=4, bnpl_paid=2),
            _item("tabby2", "RIYAD", 20, -300, ["TABBY *{n} OF 6 INSTAL", "POS TABBY PAYMENT"], None, None,
                  bnpl_total=6, bnpl_paid=3),
            _item("netflix", "ALRAJHI", 8, -65, ["NETFLIX.COM AMSTERDAM NL"], "Netflix", "subscription"),
            _item("stc", "ALRAJHI", 10, -320, ["SADAD BILL - STC", "سداد - فاتورة STC"], "STC", None, jitter=0.05),
            _item("kahraba", "ALRAJHI", 15, -280, ["SADAD BILL - KAHRABA", "سداد - شركة الكهرباء"], None, "bills", jitter=0.2),
        ],
        "flexible": {
            "groceries": {"monthly": 1200, "count": 5, "bank": "ALRAJHI",
                          "descs": ["POS PANDA RETAIL RIYADH", "POS TAMIMI MARKETS 112", "POS OTHAIM MRKT"]},
            "cafes": {"monthly": 550, "count": 7, "bank": "ALRAJHI",
                      "descs": ["POS BARNS COFFEE 4421 RIYADH", "POS HALF MILLION RUH", "مقهى دوز - رياض"]},
            "restaurants": {"monthly": 800, "count": 5, "bank": "ALRAJHI",
                            "descs": ["POS ALBAIK KHURAIS RD", "HUNGERSTATION RIYADH", "POS SHAWARMA HOUSE"]},
            "fuel": {"monthly": 450, "count": 4, "bank": "SNB",
                     "descs": ["POS SASCO FUEL 0091", "POS ALDREES PETROL"]},
            "shopping": {"monthly": 900, "count": 3, "bank": "RIYAD",
                         "descs": ["POS AMAZON.SA RETAIL", "POS EXTRA STORES RUH", "POS ZARA GRANADA MALL"]},
            "entertainment": {"monthly": 300, "count": 2, "bank": "ALRAJHI",
                              "descs": ["VOX CINEMAS RIYADH FRONT", "POS PLAYSTATION NETWORK"]},
        },
        "current_month_pace": {},
    }


def _sara_spec() -> dict:
    """Healthy customer: strong salary, one loan, no BNPL — the go-ahead case."""
    return {
        "customer": _customer("CUST002", "sara", "سارة ", "Sara Alharbi", "1000000002",
                              date(1988, 11, 20), 22000, "Jeddah", "Government", "Ministry Entity"),
        "accounts": [
            _account("ACC002-RAJ", "CUST002", "ALRAJHI", "current", 54000, True),
            _account("ACC002-RAJS", "CUST002", "ALRAJHI", "savings", 35000, False),
            _account("ACC002-SAB", "CUST002", "SAB", "current", 4200, False),
        ],
        "loans": [
            {"loan_id": "LN002", "bank_code": "ALRAJHI", "loan_type": "car", "total": 76800,
             "installment": 1600, "remaining_months": 14, "months_paid": 34, "day": 5},
        ],
        "salary": {"amount": 22000, "day": 25, "bank": "ALRAJHI", "day_overrides": {},
                   "descs": ["MUDAD PAYROLL MOF ENTITY", "حوالة راتب حكومي"]},
        "recurring": [
            _item("loan_raj", "ALRAJHI", 5, -1600, ["ALRAJHI AUTO FIN INSTALLMENT", "قسط تمويل سيارة - الراجحي"], None, None,
                  months_paid=34),
            _item("stc", "ALRAJHI", 10, -250, ["SADAD BILL - STC"], "STC", "bills", jitter=0.05),
            _item("shahid", "ALRAJHI", 6, -28, ["SHAHID VIP SUBSCRIPTION"], "Shahid", "subscription"),
            _item("kahraba", "ALRAJHI", 15, -220, ["SADAD BILL - KAHRABA"], None, "bills", jitter=0.2),
        ],
        "flexible": {
            "groceries": {"monthly": 1400, "count": 5, "bank": "ALRAJHI",
                          "descs": ["POS DANUBE JEDDAH 12", "POS TAMIMI MARKETS JED"]},
            "cafes": {"monthly": 420, "count": 5, "bank": "ALRAJHI",
                      "descs": ["POS BREW92 JEDDAH", "مقهى الغيمة - جدة"]},
            "restaurants": {"monthly": 950, "count": 4, "bank": "ALRAJHI",
                            "descs": ["POS ALROMANSIAH JED", "HUNGERSTATION JEDDAH"]},
            "shopping": {"monthly": 1300, "count": 3, "bank": "SAB",
                         "descs": ["POS AMAZON.SA RETAIL", "POS RED SEA MALL STORE"]},
            "fuel": {"monthly": 380, "count": 3, "bank": "ALRAJHI", "descs": ["POS ALDREES PETROL JED"]},
            "entertainment": {"monthly": 350, "count": 2, "bank": "ALRAJHI", "descs": ["VOX CINEMAS RED SEA MALL"]},
        },
        "current_month_pace": {},
    }


def _khalid_spec() -> dict:
    """Radar customer: current-month cafe spending pace is on course to miss the loan installment."""
    return {
        "customer": _customer("CUST003", "khalid", "خالد ", "Khalid Alshehri", "1000000003",
                              date(1994, 2, 5), 14500, "Dammam", "Private", "Eastern Services Ltd."),
        "accounts": [
            _account("ACC003-RAJ", "CUST003", "ALRAJHI", "current", 4850, True),
            _account("ACC003-SNB", "CUST003", "SNB", "current", 1150, False),
        ],
        "loans": [
            {"loan_id": "LN003", "bank_code": "RIYAD", "loan_type": "car", "total": 111600,
             "installment": 3100, "remaining_months": 22, "months_paid": 14, "day": 27},
        ],
        # Salary on day 1: already received this month, so overspending eats real balance.
        "salary": {"amount": 14500, "day": 1, "bank": "ALRAJHI", "day_overrides": {},
                   "descs": ["MUDAD PAYROLL EASTERN SVCS", "حوالة راتب"]},
        "recurring": [
            _item("rent", "ALRAJHI", 2, -3800, ["SADAD RENT EJAR PLATFORM", "ايجار شقة - العزيزية"], None, "housing"),
            _item("loan_ryd", "RIYAD", 27, -3100, ["RIYAD BANK AUTO INSTALLMENT {n2}/36", "قسط سيارة - بنك الرياض"], None, None,
                  months_paid=14),
            _item("tabby", "SNB", 21, -220, ["POS TABBY* PAYMENT DMM", "TABBY *{n} OF 4 INSTAL"], None, None,
                  bnpl_total=4, bnpl_paid=1),
            _item("stc", "ALRAJHI", 10, -300, ["SADAD BILL - STC"], "STC", "bills", jitter=0.05),
        ],
        "flexible": {
            "groceries": {"monthly": 900, "count": 4, "bank": "ALRAJHI",
                          "descs": ["POS PANDA RETAIL DAMMAM", "POS OTHAIM MRKT DMM"]},
            "cafes": {"monthly": 480, "count": 10, "bank": "ALRAJHI",
                      "descs": ["POS BARNS COFFEE 1180 DMM", "POS RAVE COFFEE KHOBAR", "مقهى سكرة - الدمام"]},
            "restaurants": {"monthly": 750, "count": 5, "bank": "ALRAJHI",
                            "descs": ["POS HERFY KHOBAR", "JAHEZ ORDER DAMMAM", "POS MAESTRO PIZZA"]},
            "fuel": {"monthly": 420, "count": 4, "bank": "SNB", "descs": ["POS SASCO FUEL DMM"]},
            "entertainment": {"monthly": 250, "count": 2, "bank": "ALRAJHI", "descs": ["POS PLAYSTATION NETWORK"]},
        },
        # Current-month acceleration: cafes more than doubled, restaurants slightly up.
        # This is what the radar's pace math must catch.
        "current_month_pace": {"cafes": 2.2, "restaurants": 1.15},
        # The generator derives the primary balance so the projected gap before the
        # loan installment lands near this value whatever day the data is seeded.
        "radar_gap_target": 340,
    }


def _noura_spec() -> dict:
    """Overstretched customer: three BNPL stacks, thin savings — the avoid case."""
    return {
        "customer": _customer("CUST004", "noura", "نورة ", "Noura Alqahtani", "1000000004",
                              date(1997, 8, 30), 9500, "Riyadh", "Private", "Retail Group Co."),
        "accounts": [
            _account("ACC004-SNB", "CUST004", "SNB", "current", 2100, True),
            _account("ACC004-RAJ", "CUST004", "ALRAJHI", "current", 600, False),
        ],
        "loans": [
            {"loan_id": "LN004", "bank_code": "SNB", "loan_type": "personal", "total": 68400,
             "installment": 1900, "remaining_months": 18, "months_paid": 18, "day": 5},
        ],
        "salary": {"amount": 9500, "day": 25, "bank": "SNB", "day_overrides": {},
                   "descs": ["MUDAD PAYROLL RETAIL GROUP", "حوالة راتب"]},
        "recurring": [
            _item("rent", "SNB", 3, -3500, ["SADAD RENT EJAR PLATFORM", "ايجار استوديو - النرجس"], None, "housing"),
            _item("loan_snb", "SNB", 5, -1900, ["SNB PERSONAL FIN INSTALLMENT {n2}/36"], None, None, months_paid=18),
            _item("jamiya", "ALRAJHI", 7, -500, ["حوالة - جمعية زميلات العمل"], None, None),
            _item("tabby1", "SNB", 9, -350, ["POS TABBY* PAYMENT RUH", "TABBY *{n} OF 6 INSTAL"], None, None,
                  bnpl_total=6, bnpl_paid=2),
            _item("tamara", "ALRAJHI", 14, -280, ["تمارا - قسط {n} من 4"], None, None,
                  bnpl_total=4, bnpl_paid=1),
            _item("tabby2", "SNB", 19, -190, ["TABBY *{n} OF 4 INSTAL", "POS TABBY PAYMENT"], None, None,
                  bnpl_total=4, bnpl_paid=2),
            _item("stc", "SNB", 10, -250, ["SADAD BILL - STC"], "STC", "bills", jitter=0.05),
        ],
        "flexible": {
            "groceries": {"monthly": 700, "count": 4, "bank": "SNB", "descs": ["POS PANDA RETAIL RIYADH"]},
            "cafes": {"monthly": 380, "count": 6, "bank": "SNB",
                      "descs": ["POS HALF MILLION RUH", "مقهى نص مليون"]},
            "restaurants": {"monthly": 600, "count": 4, "bank": "SNB", "descs": ["HUNGERSTATION RIYADH"]},
            "shopping": {"monthly": 520, "count": 3, "bank": "ALRAJHI",
                         "descs": ["POS SHEIN.COM", "POS NAMSHI GENERAL TRADING"]},
        },
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
    digits = f"{abs(hash(account_id)) % 10**18:018d}"
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


def _tune_radar_balance(spec: dict, today: date, rows: list[dict]) -> None:
    """Derive the radar customer's primary balance so the demo gap is stable.

    The radar demo must fire whatever day the data is seeded, so the balance is
    computed backwards from the loan installment date using the SAME pace math
    the radar runs over the actually rendered month-to-date transactions.
    Seeding on/after the installment day leaves the balance as-is (belt-secure demo).
    """
    target = spec.get("radar_gap_target")
    if not target:
        return
    loan = spec["loans"][0]
    if today.day >= loan["day"]:
        return
    current_month = today.isoformat()[:7]
    mtd_flexible = sum(
        abs(row["amount"]) for row in rows
        if row.get("_flex") and str(row["transaction_date"]).startswith(current_month)
    )
    pace = mtd_flexible / today.day if today.day >= 3 and mtd_flexible else sum(
        plan["monthly"] * spec["current_month_pace"].get(category, 1.0)
        for category, plan in spec["flexible"].items()
    ) / 30
    upcoming = sum(
        -item["amount"] for item in spec["recurring"]
        if today.day < item["day"] < loan["day"] and _item_active(item, 0)
    )
    needed = loan["installment"] - target + pace * (loan["day"] - today.day) + upcoming
    primary = next(a for a in spec["accounts"] if a["is_primary"])
    others = sum(a["balance"] for a in spec["accounts"] if not a["is_primary"])
    primary["balance"] = max(round(needed - others), 500)


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
        for _ in range(count):
            day = rng.randint(1, last_day)
            # Wide multiplicative spread: real discretionary spend swings a lot per
            # purchase (a coffee vs a group dinner). This irregular amount is what
            # keeps flexible spending from masquerading as a fixed monthly obligation.
            amount = -round(month_total / count * rng.uniform(0.35, 2.3))
            # Real cross-bank feeds rarely carry clean categories: drop some on purpose.
            # Dropping is uniform across months, so radar pace ratios stay unbiased.
            keep_category = rng.random() > 0.15
            row = _txn(spec, plan["bank"], _shift_month(today, month_offset, day),
                       amount, rng.choice(plan["descs"]),
                       None, category if keep_category else None, "expense")
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
        "category": category,
        "raw_description": desc,
        "amount": float(amount),
        "transaction_type": txn_type,
        "channel": "pos" if desc.startswith("POS") else "transfer",
        "created_at": _now(),
    }


def _shift_month(today: date, month_offset: int, day: int) -> date:
    """Return the given day in the month offset from today, clamped to month length."""
    total = today.year * 12 + (today.month - 1) + month_offset
    year, month = divmod(total, 12)
    month += 1
    return date(year, month, min(day, monthrange(year, month)[1]))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
