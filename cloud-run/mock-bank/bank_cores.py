"""The banks' core systems: a SEPARATE BigQuery dataset served by this gateway.

Like a real bank API, there is a database behind the endpoints — the `bank_cores`
dataset, seeded by the demo world generator. This service only ever READS it,
and it has no access to Edraak's own warehouse: data still crosses to Edraak
exclusively through the consented API pull.

Rows are cached in memory with a short TTL so serving stays instant while the
daily auto-seed (run by the Edraak backend) is picked up within minutes.
"""
import logging
import os
import time


logger = logging.getLogger("gateway.cores")

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "")
DATASET = os.getenv("BANK_CORES_DATASET", "bank_cores")
CACHE_TTL_SECONDS = 300

_cache: dict = {"loaded_at": 0.0, "accounts": [], "transactions": [], "loans": []}
_client = None


def customer_accounts(customer_id: str, bank_code: str) -> list[dict]:
    """Accounts this customer holds at this specific bank."""
    _ensure_fresh()
    return [a for a in _cache["accounts"]
            if a["customer_id"] == customer_id and a["bank_code"] == bank_code.upper()]


def account_transactions(customer_id: str, account_id: str) -> list[dict]:
    """Booked transactions for one account, newest first."""
    _ensure_fresh()
    rows = [t for t in _cache["transactions"]
            if t["customer_id"] == customer_id and t.get("account_id") == account_id]
    return sorted(rows, key=lambda t: str(t.get("transaction_date", "")), reverse=True)


def customer_loans(customer_id: str, bank_code: str) -> list[dict]:
    """Active financing products this customer holds at this specific bank."""
    _ensure_fresh()
    return [l for l in _cache["loans"]
            if l["customer_id"] == customer_id and l["bank_code"] == bank_code.upper()]


def core_stats() -> list[dict]:
    """Row counts per bank — a read-only peek at the cores without exposing data."""
    _ensure_fresh()
    banks: dict[str, dict] = {}
    for a in _cache["accounts"]:
        banks.setdefault(a["bank_code"], {"accounts": 0, "transactions": 0})["accounts"] += 1
    for t in _cache["transactions"]:
        banks.setdefault(t["bank_code"], {"accounts": 0, "transactions": 0})["transactions"] += 1
    return [{"bank_code": code, **counts} for code, counts in sorted(banks.items())]


def _ensure_fresh() -> None:
    """Reload the cores from BigQuery when the cache is older than the TTL."""
    if time.time() - _cache["loaded_at"] < CACHE_TTL_SECONDS and _cache["accounts"]:
        return
    client = _bq()
    for table in ("accounts", "transactions", "loans"):
        rows = [dict(r) for r in client.query(
            f"SELECT * FROM `{PROJECT_ID}.{DATASET}.{table}`").result()]
        for row in rows:  # dates/timestamps -> ISO strings for JSON serialization
            for key, value in row.items():
                if hasattr(value, "isoformat"):
                    row[key] = value.isoformat()
        _cache[table] = rows
    _cache["loaded_at"] = time.time()
    logger.info("gateway.cores.loaded accounts=%s transactions=%s loans=%s message=Bank cores cached from BigQuery",
                len(_cache["accounts"]), len(_cache["transactions"]), len(_cache["loans"]))


def _bq():
    global _client
    if _client is None:
        from google.cloud import bigquery

        if not PROJECT_ID:
            raise RuntimeError("GCP_PROJECT_ID is required for the mock gateway's bank cores.")
        _client = bigquery.Client(project=PROJECT_ID)
    return _client
