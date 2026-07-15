"""Mock SAMA Open Banking gateway — a standalone Cloud Run service that plays the banks.

Runs on its own domain and uses only the separate ``bank_cores`` BigQuery
dataset. Data crosses into Edraak's ``edraak_finance`` warehouse only through a
consented API pull; the consent gate returns 403 without a valid consent.

The JSON shape follows the UK-OBIE style the KSA standard is based on. The licensed
field-level spec is distributed via SAMA's Open Banking Lab; this is a simulation.
"""
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Form, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

import bank_cores


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("gateway")

CONSENT_TTL_DAYS = 365
DEFAULT_PERMISSIONS = [
    "ReadAccountsBasic", "ReadBalances", "ReadTransactionsDetail",
    "ReadBeneficiaries", "ReadStandingOrders",
]

# Arabic bank names and the standard's per-bank quirks: the envelope is fixed, but
# banks differ in which optional fields they fill — the messiness Edraak absorbs.
BANKS = {
    "ALINMA": {"name_ar": "مصرف الإنماء", "include_merchant": True, "issuer": "INMA"},
    "ALRAJHI": {"name_ar": "مصرف الراجحي", "include_merchant": False, "issuer": "ARB"},
    "SNB": {"name_ar": "البنك الأهلي السعودي", "include_merchant": True, "issuer": "SNB"},
    "RIYAD": {"name_ar": "بنك الرياض", "include_merchant": False, "issuer": "RIBL"},
    "SAB": {"name_ar": "البنك السعودي الأول", "include_merchant": True, "issuer": "SABB"},
}

TEMPLATES = Path(__file__).parent / "templates"

# Consents held on the BANK side are durable append-only versions in
# bank_cores.consents. Edraak (the TPP) keeps its own record separately.
DEMO_RESET_TOKEN = os.getenv("DEMO_RESET_TOKEN", "edraak-demo-reset")

app = FastAPI(
    title="SAMA Open Banking Mock — KSAOB v1",
    description=(
        "Simulated KSA Open Banking (AIS) gateway for the Edraak demo. "
        "Flow: create a consent (POST /{bank_code}/open-banking/v1/consents), the "
        "customer authorises it on the bank's own screen (GET /{bank_code}/authorize), "
        "then every data call carries the ConsentId in the `x-consent-id` header. "
        "Without an Authorised consent, data endpoints return 403 — consent is the gate."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


@app.on_event("startup")
def prepare_runtime_schema():
    """Keep local runs compatible with additive gateway schema updates."""
    bank_cores.ensure_runtime_tables()


class ConsentRequest(BaseModel):
    customer_id: str
    permissions: list[str] = DEFAULT_PERMISSIONS
    redirect_uri: str | None = None


class DemoResetRequest(BaseModel):
    customer_id: str


@app.get("/", response_class=HTMLResponse, tags=["Info"])
def landing():
    """A tiny landing page pointing at the interactive API docs."""
    banks = "".join(f"<li><b>{code}</b> — {b['name_ar']}</li>" for code, b in BANKS.items())
    return f"""
    <html dir="rtl" lang="ar"><head><meta charset="utf-8">
    <title>SAMA Open Banking Mock</title>
    <style>body{{font-family:Tahoma,Arial;background:#0a1c2b;color:#e7f0f7;max-width:720px;margin:40px auto;padding:24px;line-height:1.9}}
    a{{color:#6bb8ff}} code{{background:#122a3d;padding:2px 6px;border-radius:4px}}</style></head>
    <body>
    <h1>بوابة المصرفية المفتوحة (محاكاة KSAOB)</h1>
    <p>هذه خدمة مستقلة تُحاكي بوابات البنوك تحت معيار البنك المركزي السعودي. البيانات تعيش هنا داخل البنوك،
    ولا تنتقل إلى إدراك إلا بعد موافقة العميل عبر واجهة برمجية.</p>
    <p>البنوك المتاحة:</p><ul>{banks}</ul>
    <p>جرّب الواجهات تفاعليًا: <a href="/docs">صفحة توثيق الواجهات (Swagger)</a></p>
    <p>لا تملك هذه الخدمة أي صلاحية على قاعدة بيانات إدراك — الجسر الوحيد هو الواجهة البرمجية بعد الموافقة.</p>
    </body></html>
    """


@app.post("/{bank_code}/open-banking/v1/consents", status_code=201, tags=["Consents"])
def create_consent(bank_code: str, body: ConsentRequest):
    """Create a consent in AwaitingAuthorisation and return where the customer must approve it."""
    _require_bank(bank_code)
    now = datetime.now(timezone.utc)
    consent_id = f"CONS-{uuid4().hex[:10].upper()}"
    consent = {
        "consent_id": consent_id,
        "customer_id": body.customer_id,
        "bank_code": bank_code.upper(),
        "permissions": body.permissions,
        "status": "AwaitingAuthorisation",
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(days=CONSENT_TTL_DAYS)).isoformat(),
        "redirect_uri": body.redirect_uri,
    }
    bank_cores.save_consent(consent)
    logger.info("flow.gateway.consent.created bank=%s customer_id=%s consent_id=%s status=AwaitingAuthorisation",
                bank_code, body.customer_id, consent_id)
    return {
        "Data": {
            "ConsentId": consent_id,
            "Status": "AwaitingAuthorisation",
            "Permissions": body.permissions,
            "ExpirationDateTime": consent["expires_at"],
            "AuthorizeUrl": f"/{bank_code.upper()}/authorize?consent_id={consent_id}",
        }
    }


@app.get("/{bank_code}/authorize", response_class=HTMLResponse, tags=["Consents"])
def authorize_page(bank_code: str, consent_id: str):
    """The BANK's own approval screen — the redirect target where the customer taps السماح."""
    bank = _require_bank(bank_code)
    consent = bank_cores.get_consent(consent_id)
    if not consent or consent["bank_code"] != bank_code.upper():
        raise HTTPException(status_code=404, detail=_error("U404", "Unknown ConsentId for this bank."))
    template = (TEMPLATES / "authorize.html").read_text(encoding="utf-8")
    expires = str(consent["expires_at"])[:10]
    return (
        template
        .replace("{{BANK_NAME}}", bank["name_ar"])
        .replace("{{CONSENT_ID}}", consent_id)
        .replace("{{BANK_CODE}}", bank_code.upper())
        .replace("{{EXPIRES}}", expires)
    )


@app.post("/{bank_code}/authorize", tags=["Consents"])
def authorize_submit(bank_code: str, consent_id: str = Form(...), decision: str = Form(...)):
    """Handle السماح / رفض, then redirect back to Edraak with the result."""
    _require_bank(bank_code)
    consent = bank_cores.get_consent(consent_id)
    if not consent or consent["bank_code"] != bank_code.upper():
        raise HTTPException(status_code=404, detail=_error("U404", "Unknown ConsentId for this bank."))
    consent["status"] = "Authorised" if decision == "allow" else "Rejected"
    bank_cores.save_consent(consent)
    logger.info("flow.gateway.consent.decided bank=%s consent_id=%s status=%s", bank_code, consent_id, consent["status"])
    redirect = consent.get("redirect_uri")
    if redirect:
        sep = "&" if "?" in redirect else "?"
        return RedirectResponse(
            url=f"{redirect}{sep}consent_id={consent_id}&bank={bank_code.upper()}&status={consent['status']}",
            status_code=303,
        )
    # No redirect target (the app polls): show a friendly result page in the tab.
    approved = consent["status"] == "Authorised"
    title = "تمت الموافقة ✓" if approved else "تم الرفض"
    body = ("تمت مشاركة بياناتك مع إدراك. يمكنك إغلاق هذه الصفحة والعودة إلى التطبيق."
            if approved else "لم تتم مشاركة أي بيانات. يمكنك إغلاق هذه الصفحة.")
    color = "#37d6a6" if approved else "#f0736a"
    auto_close = """
      <script>
        if (window.opener) {
          window.setTimeout(() => window.close(), 1200);
        }
      </script>
    """ if approved else ""
    return HTMLResponse(f"""
    <html dir="rtl" lang="ar"><head><meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1"><title>{title}</title>
    <style>body{{font-family:Tahoma,Arial;background:#0a1622;color:#e9f1f8;height:100vh;margin:0;
    display:grid;place-items:center;text-align:center;padding:24px}}
    .c{{max-width:380px}} h1{{color:{color};font-size:26px}} p{{color:#a9c2d6;line-height:1.9}}
    button{{margin-top:20px;padding:13px 22px;border:0;border-radius:12px;background:{color};
    color:#03140d;font-size:16px;font-weight:800;cursor:pointer}}</style></head>
    <body><div class="c"><h1>{title}</h1><p>{body}</p>
    <button type="button" onclick="window.close()">العودة إلى إدراك</button></div>
    {auto_close}</body></html>
    """)


@app.get("/{bank_code}/open-banking/v1/consents/{consent_id}", tags=["Consents"])
def get_consent(bank_code: str, consent_id: str):
    """Read one consent's status — lets Edraak poll until the customer approves."""
    consent = bank_cores.get_consent(consent_id)
    if not consent or consent["bank_code"] != bank_code.upper():
        raise HTTPException(status_code=404, detail=_error("U404", "Unknown ConsentId for this bank."))
    return {"Data": {
        "ConsentId": consent_id,
        "Status": consent["status"] if _is_live(consent) else "Expired",
        "ExpirationDateTime": consent["expires_at"],
        "Permissions": consent["permissions"],
    }}


@app.delete("/{bank_code}/open-banking/v1/consents/{consent_id}", tags=["Consents"])
def revoke_consent(bank_code: str, consent_id: str):
    """Revoke a consent — after this, data calls return 403 again (a live proof moment)."""
    consent = bank_cores.get_consent(consent_id)
    if not consent or consent["bank_code"] != bank_code.upper():
        raise HTTPException(status_code=404, detail=_error("U404", "Unknown ConsentId for this bank."))
    consent["status"] = "Revoked"
    bank_cores.save_consent(consent)
    logger.info("flow.gateway.consent.revoked bank=%s consent_id=%s", bank_code, consent_id)
    return {"Data": {"ConsentId": consent_id, "Status": "Revoked"}}


@app.get("/{bank_code}/open-banking/v1/accounts", tags=["Accounts"])
def list_accounts(bank_code: str, x_consent_id: str | None = Header(None)):
    """List the consented customer's accounts at this bank, KSAOB-shaped."""
    consent = _require_consent(bank_code, x_consent_id)
    rows = bank_cores.customer_accounts(consent["customer_id"], bank_code)
    logger.info("flow.gateway.accounts bank=%s customer_id=%s rows=%s", bank_code, consent["customer_id"], len(rows))
    return {"Data": {"Account": [_ob_account(r) for r in rows]}, "Meta": {"TotalRecords": len(rows)}}


@app.get("/{bank_code}/open-banking/v1/accounts/{account_id}/balances", tags=["Accounts"])
def get_balances(bank_code: str, account_id: str, x_consent_id: str | None = Header(None)):
    """Return the current balance of one account."""
    consent = _require_consent(bank_code, x_consent_id)
    row = next((r for r in bank_cores.customer_accounts(consent["customer_id"], bank_code)
                if r["account_id"] == account_id), None)
    if row is None:
        raise HTTPException(status_code=404, detail=_error("U404", "Unknown AccountId for this consent."))
    return {"Data": {"Balance": [_ob_balance(row)]}}


@app.get("/{bank_code}/open-banking/v1/accounts/{account_id}/transactions", tags=["Transactions"])
def list_transactions(bank_code: str, account_id: str,
                      page: int = Query(1, ge=1), page_size: int = Query(100, ge=1, le=500),
                      x_consent_id: str | None = Header(None)):
    """Return one page of booked transactions for one account, KSAOB envelope."""
    consent = _require_consent(bank_code, x_consent_id)
    bank = BANKS[bank_code.upper()]
    rows = bank_cores.account_transactions(consent["customer_id"], account_id)
    total_pages = max((len(rows) + page_size - 1) // page_size, 1)
    window = rows[(page - 1) * page_size: page * page_size]
    logger.info("flow.gateway.transactions bank=%s account_id=%s page=%s rows=%s",
                bank_code, account_id, page, len(window))
    return {
        "Data": {"Transaction": [_ob_transaction(t, bank) for t in window]},
        "Meta": {"TotalRecords": len(rows), "TotalPages": total_pages, "Page": page},
    }


@app.get("/{bank_code}/open-banking/v1/loans", tags=["Loans"])
def list_loans(bank_code: str, x_consent_id: str | None = Header(None)):
    """Active financing products at this bank for the consented customer.

    DESIGN NOTE: KSAOB AIS phase 1 does not expose loans; this is a simulated
    product-data extension so cross-bank loans arrive the honest way — through
    the bank's own API after consent — instead of a magic bureau feed.
    """
    consent = _require_consent(bank_code, x_consent_id)
    rows = bank_cores.customer_loans(consent["customer_id"], bank_code)
    logger.info("flow.gateway.loans bank=%s customer_id=%s rows=%s", bank_code, consent["customer_id"], len(rows))
    return {"Data": {"Loan": rows}, "Meta": {"TotalRecords": len(rows)}}


@app.get("/{bank_code}/_core/stats", tags=["Info"])
def core_stats(bank_code: str):
    """Read-only row counts for a bank's core — point at the data without moving it."""
    _require_bank(bank_code)
    stats = next((s for s in bank_cores.core_stats() if s["bank_code"] == bank_code.upper()), None)
    return stats or {"bank_code": bank_code.upper(), "accounts": 0, "transactions": 0}


@app.post("/internal/demo-reset", include_in_schema=False)
def demo_reset(body: DemoResetRequest, x_demo_reset_token: str | None = Header(None)):
    """Backend-only presentation control: revoke a customer's bank-side consents."""
    if x_demo_reset_token != DEMO_RESET_TOKEN:
        raise HTTPException(status_code=403, detail=_error("U009", "Invalid demo reset token."))
    revoked = bank_cores.revoke_customer_consents(body.customer_id)
    logger.warning("flow.gateway.demo_reset customer_id=%s revoked=%s", body.customer_id, revoked)
    return {"status": "reset", "customer_id": body.customer_id, "revoked_consents": revoked}


@app.post("/internal/core-cache/invalidate", include_in_schema=False)
def invalidate_core_cache(x_demo_reset_token: str | None = Header(None)):
    """Backend-only hook called after the synthetic core tables are replaced."""
    if x_demo_reset_token != DEMO_RESET_TOKEN:
        raise HTTPException(status_code=403, detail=_error("U009", "Invalid demo reset token."))
    bank_cores.invalidate_core_cache()
    return {"status": "invalidated"}


def _require_bank(bank_code: str) -> dict:
    if bank_code.upper() not in BANKS:
        raise HTTPException(status_code=404, detail=_error("U404", f"Unknown bank_code {bank_code!r}."))
    return BANKS[bank_code.upper()]


def _require_consent(bank_code: str, consent_id: str | None) -> dict:
    """The gate: every data endpoint needs an Authorised, live consent for this exact bank."""
    _require_bank(bank_code)
    if not consent_id:
        raise HTTPException(status_code=401, detail=_error(
            "U001", "Missing x-consent-id header. Create and authorise a consent first."))
    consent = bank_cores.get_consent(consent_id)
    if not consent or consent["bank_code"] != bank_code.upper():
        raise HTTPException(status_code=403, detail=_error(
            "U007", "Consent not valid for this bank. Data moves only after customer consent."))
    if consent["status"] != "Authorised":
        raise HTTPException(status_code=403, detail=_error(
            "U006", f"Consent is {consent['status']}, not Authorised. The customer must approve it first."))
    if not _is_live(consent):
        raise HTTPException(status_code=403, detail=_error("U008", "Consent expired. Ask the customer again."))
    return consent


def _is_live(consent: dict) -> bool:
    return datetime.now(timezone.utc) < datetime.fromisoformat(str(consent["expires_at"]))


def _ob_account(row: dict) -> dict:
    return {
        "AccountId": row["account_id"],
        "Currency": "SAR",
        "AccountType": "Personal",
        "AccountSubType": "CurrentAccount" if row.get("account_type") == "current" else "Savings",
        "Nickname": row.get("bank_name_ar"),
        "Account": [{"SchemeName": "IBAN", "Identification": row.get("iban")}],
    }


def _ob_balance(row: dict) -> dict:
    return {
        "AccountId": row["account_id"],
        "CreditDebitIndicator": "Credit",
        "Type": "InterimAvailable",
        "Amount": {"Amount": f"{float(row.get('balance') or 0):.2f}", "Currency": "SAR"},
    }


def _ob_transaction(row: dict, bank: dict) -> dict:
    amount = float(row.get("amount") or 0)
    payload = {
        "AccountId": row.get("account_id"),
        "TransactionId": row["transaction_id"],
        "CreditDebitIndicator": "Credit" if amount > 0 else "Debit",
        "Status": "Booked",
        "BookingDateTime": f"{str(row.get('transaction_date', ''))[:10]}T09:00:00+03:00",
        "Amount": {"Amount": f"{abs(amount):.2f}", "Currency": "SAR"},
        "TransactionInformation": row.get("raw_description") or "",
        "ProprietaryBankTransactionCode": {"Code": (row.get("channel") or "pos").upper(), "Issuer": bank["issuer"]},
    }
    # Optional-field variance: some banks populate MerchantDetails, others never do.
    if bank["include_merchant"] and row.get("merchant"):
        payload["MerchantDetails"] = {"MerchantName": row["merchant"]}
    return payload


def _error(code: str, message: str) -> dict:
    return {"Errors": [{"ErrorCode": code, "Message": message}]}
