"""Ingestion pipeline: pull a consented bank's data through the KSAOB gateway into BigQuery.

The medallion flow for one bank:
  gateway (RAM, another service)  --consented API-->  BRONZE ob_raw_payloads (raw JSON)
                                                 -->  SILVER accounts / transactions / loans
Only banks the customer has consented to ever reach the warehouse. This is the
data-pipeline story made real: no consent id, no data.

Speed notes: the gateway pulls are millisecond-fast; BigQuery round-trips dominate,
so bronze lands as ONE batched insert, the per-table DELETEs run as ONE scripted
job, and the silver load jobs run in parallel.
"""
import json
import logging
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from uuid import uuid4

from app import config
from app.data.bigquery_client import (
    clear_detected_obligations,
    clear_transaction_classifications,
    get_connected_banks,
    ingest_silver,
    save_consent,
    save_raw_payloads,
)


logger = logging.getLogger("edraak.ingestion")

PAGE_SIZE = 500


class IngestionError(RuntimeError):
    pass


def reset_gateway_consents(customer_id: str) -> int:
    """Revoke every bank-side consent for one demo customer."""
    url = f"{config.openbanking_gateway_url()}/internal/demo-reset"
    body = json.dumps({"customer_id": customer_id}).encode()
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "x-demo-reset-token": config.demo_reset_token(),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode())
        return int(payload.get("revoked_consents", 0))
    except Exception as exc:
        logger.exception("demo_reset.gateway_failed customer_id=%s url=%s", customer_id, url)
        raise IngestionError("تعذر فصل موافقات البنوك من بوابة العرض.") from exc


def ingest_bank(customer_id: str, bank_code: str, consent_id: str) -> dict:
    """Pull accounts + balances + transactions + loans for one bank, land bronze→silver."""
    bank_code = bank_code.upper()
    logger.info("flow.ingest.start customer_id=%s bank=%s consent_id=%s message=Pulling from KSAOB gateway",
                customer_id, bank_code, consent_id)
    consent_doc = _assert_authorised(bank_code, consent_id)
    bronze: list[dict] = []

    # Hide the warehouse round-trip needed for safe re-linking behind the first
    # gateway pull instead of making the presenter wait for both sequentially.
    with ThreadPoolExecutor(max_workers=2) as prefetch:
        connected_future = prefetch.submit(get_connected_banks, customer_id)
        accounts_future = prefetch.submit(
            _get, bank_code, "/open-banking/v1/accounts", consent_id
        )
        accounts_doc = accounts_future.result()
    bronze.append(_bronze_row(customer_id, bank_code, consent_id, "accounts", None, 1, accounts_doc))

    def pull_account(ob_account: dict) -> tuple[dict, list[dict], list[dict]]:
        account_id = ob_account["AccountId"]
        account_bronze: list[dict] = []
        balance_doc = _get(bank_code, f"/open-banking/v1/accounts/{account_id}/balances", consent_id)
        account_bronze.append(
            _bronze_row(customer_id, bank_code, consent_id, "balances", account_id, 1, balance_doc)
        )
        transactions = _pull_transactions(
            customer_id, bank_code, account_id, consent_id, account_bronze
        )
        return (
            _silver_account(customer_id, bank_code, ob_account, balance_doc),
            transactions,
            account_bronze,
        )

    ob_accounts = accounts_doc.get("Data", {}).get("Account", [])
    account_rows, txn_rows = [], []
    # Al Rajhi intentionally carries all external demo accounts. Pull each
    # account in parallel, alongside the loans endpoint, to keep the one link fast.
    with ThreadPoolExecutor(max_workers=max(min(len(ob_accounts) + 1, 8), 1)) as pool:
        loans_future = pool.submit(_get, bank_code, "/open-banking/v1/loans", consent_id)
        for account, transactions, account_bronze in pool.map(pull_account, ob_accounts):
            account_rows.append(account)
            txn_rows.extend(transactions)
            bronze.extend(account_bronze)
        loans_doc = loans_future.result()
    bronze.append(_bronze_row(customer_id, bank_code, consent_id, "loans", None, 1, loans_doc))
    loan_rows = loans_doc.get("Data", {}).get("Loan", [])

    # BigQuery round-trips dominate this flow, so independent bronze, silver,
    # cache-invalidation, and consent writes run concurrently.
    already_linked = bank_code in connected_future.result()
    silver = {
        "accounts": account_rows,
        "transactions": txn_rows,
        "loans": loan_rows,
    }
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [
            pool.submit(save_raw_payloads, bronze),
            pool.submit(ingest_silver, customer_id, bank_code, silver, already_linked),
            pool.submit(clear_detected_obligations, customer_id),
            pool.submit(clear_transaction_classifications, customer_id),
            pool.submit(_record_consent, customer_id, bank_code, consent_id, consent_doc),
        ]
        for future in futures:
            future.result()

    logger.info("flow.ingest.completed customer_id=%s bank=%s accounts=%s transactions=%s loans=%s",
                customer_id, bank_code, len(account_rows), len(txn_rows), len(loan_rows))
    return {"bank_code": bank_code, "accounts": len(account_rows),
            "transactions": len(txn_rows), "loans": len(loan_rows)}


def _pull_transactions(customer_id: str, bank_code: str, account_id: str,
                       consent_id: str, bronze: list[dict]) -> list[dict]:
    """Page through one account's transactions, collecting bronze rows on the way."""
    rows, page = [], 1
    while True:
        path = f"/open-banking/v1/accounts/{account_id}/transactions?page={page}&page_size={PAGE_SIZE}"
        doc = _get(bank_code, path, consent_id)
        bronze.append(_bronze_row(customer_id, bank_code, consent_id, "transactions", account_id, page, doc))
        for ob_txn in doc.get("Data", {}).get("Transaction", []):
            rows.append(_silver_transaction(customer_id, bank_code, ob_txn))
        if page >= doc.get("Meta", {}).get("TotalPages", 1):
            break
        page += 1
    return rows


def _assert_authorised(bank_code: str, consent_id: str) -> dict:
    """Confirm the consent is Authorised before pulling — the gate, TPP side."""
    doc = _get(bank_code, f"/open-banking/v1/consents/{consent_id}", consent_id, gated=False)
    status = doc.get("Data", {}).get("Status")
    if status != "Authorised":
        raise IngestionError(f"الموافقة حالتها {status} وليست معتمدة — أعد ربط الحساب.")
    return doc


def _get(bank_code: str, path: str, consent_id: str, gated: bool = True) -> dict:
    """GET one KSAOB resource from the gateway with the consent header."""
    url = f"{config.openbanking_gateway_url()}/{bank_code}{path}"
    headers = {"x-consent-id": consent_id} if gated else {}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        logger.error("ingest.gateway.error url=%s status=%s body=%s", url, exc.code, body[:300])
        if exc.code == 404 and "consents" in path:
            # The gateway forgot the consent (e.g. it was restarted) — re-link.
            raise IngestionError("البنك لا يعرف هذه الموافقة — أعد ربط الحساب من جديد.") from exc
        raise IngestionError(f"بوابة البنك ردّت بخطأ {exc.code} — حاول مرة أخرى.") from exc
    except Exception as exc:
        logger.exception("ingest.gateway.unreachable url=%s", url)
        raise IngestionError("تعذر الوصول إلى بوابة المصرفية المفتوحة — تأكد أن الخدمة تعمل.") from exc


def _bronze_row(customer_id: str, bank_code: str, consent_id: str, resource: str,
                account_id: str | None, page: int, doc: dict) -> dict:
    """One raw payload exactly as received."""
    return {
        "payload_id": f"RAW-{uuid4().hex[:12]}",
        "customer_id": customer_id,
        "bank_code": bank_code,
        "consent_id": consent_id,
        "resource": resource,
        "account_id": account_id,
        "page": page,
        "raw_json": json.dumps(doc, ensure_ascii=False),
        "fetched_at": _now(),
    }


def _silver_account(customer_id: str, bank_code: str, ob_account: dict, balance_doc: dict) -> dict:
    """Normalize a KSAOB account (+ its balance) into our accounts schema."""
    identification = (ob_account.get("Account") or [{}])[0].get("Identification")
    balance = (balance_doc.get("Data", {}).get("Balance") or [{}])[0]
    amount = float(balance.get("Amount", {}).get("Amount", 0) or 0)
    return {
        "account_id": ob_account["AccountId"],
        "customer_id": customer_id,
        "bank_code": bank_code,
        "bank_name_ar": ob_account.get("Nickname"),
        "account_type": "current" if ob_account.get("AccountSubType") == "CurrentAccount" else "savings",
        "iban": identification,
        "balance": amount,
        "is_primary": False,  # a linked external bank is never the host account
        "created_at": _now(),
    }


def _silver_transaction(customer_id: str, bank_code: str, ob_txn: dict) -> dict:
    """Normalize a KSAOB transaction; meaning is classified later from raw signals."""
    amount = float(ob_txn.get("Amount", {}).get("Amount", 0) or 0)
    is_credit = ob_txn.get("CreditDebitIndicator") == "Credit"
    merchant = (ob_txn.get("MerchantDetails") or {}).get("MerchantName")
    return {
        "transaction_id": ob_txn["TransactionId"],
        "customer_id": customer_id,
        "account_id": ob_txn.get("AccountId"),
        "bank_code": bank_code,
        "transaction_date": str(ob_txn.get("BookingDateTime", ""))[:10],
        "merchant": merchant,
        "raw_description": ob_txn.get("TransactionInformation") or "",
        "amount": amount if is_credit else -amount,
        "transaction_type": "income" if is_credit else "expense",
        "channel": (ob_txn.get("ProprietaryBankTransactionCode") or {}).get("Code", "").lower() or None,
        "created_at": _now(),
    }


def _record_consent(customer_id: str, bank_code: str, consent_id: str, consent_doc: dict) -> None:
    """Write the TPP-side consent record so every ingested row traces to a consent."""
    data = consent_doc.get("Data", {})
    save_consent({
        "consent_id": consent_id,
        "customer_id": customer_id,
        "bank_code": bank_code,
        "status": data.get("Status", "Authorised"),
        "permissions": data.get("Permissions", []),
        "created_at": _now(),
        "expires_at": data.get("ExpirationDateTime"),
        "revoked_at": None,
    })


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
