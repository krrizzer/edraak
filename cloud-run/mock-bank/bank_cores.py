"""The banks' core systems: a SEPARATE BigQuery dataset served by this gateway.

Like a real bank API, there is a database behind the endpoints — the `bank_cores`
dataset, seeded by the demo world generator. This service reads the simulated
banking rows and appends durable consent-state versions there. Its code never
queries Edraak's warehouse; data crosses to Edraak exclusively through the
consented API pull.

Rows are cached in memory with a short TTL so serving stays instant while the
daily auto-seed (run by the Edraak backend) is picked up within minutes.
"""
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone


logger = logging.getLogger("gateway.cores")

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "")
DATASET = os.getenv("BANK_CORES_DATASET", "bank_cores")
CACHE_TTL_SECONDS = 300

_cache: dict = {"loaded_at": 0.0, "accounts": [], "transactions": [], "loans": []}
_consent_cache: dict[str, dict] = {}
_client = None


def ensure_runtime_tables() -> None:
    """Create the durable consent ledger when running against older demo infra."""
    from google.cloud import bigquery

    table_id = f"{PROJECT_ID}.{DATASET}.consents"
    schema = [
        bigquery.SchemaField("consent_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("customer_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("bank_code", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("permissions", "STRING", mode="REPEATED"),
        bigquery.SchemaField("status", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("expires_at", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("redirect_uri", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("updated_at", "TIMESTAMP", mode="REQUIRED"),
    ]
    try:
        _bq().create_table(bigquery.Table(table_id, schema=schema), exists_ok=True)
    except Exception as exc:
        logger.exception("gateway.runtime_table.ensure_failed table=consents")
        raise RuntimeError("Bank consent table could not be prepared.") from exc
    logger.info("gateway.runtime_table.ready table=consents")


def invalidate_core_cache() -> None:
    """Drop the in-memory bank snapshot after the generator replaces core rows."""
    _cache.update({"loaded_at": 0.0, "accounts": [], "transactions": [], "loans": []})
    logger.info("gateway.cores.cache_invalidated message=Next request will reload BigQuery")


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


def get_consent(consent_id: str) -> dict | None:
    """Read the latest append-only version of a durable bank-side consent."""
    from google.cloud import bigquery

    cached = _consent_cache.get(consent_id)
    if cached is not None:
        return dict(cached)

    rows = list(_bq().query(
        f"""
        SELECT consent_id, customer_id, bank_code, permissions, status,
               created_at, expires_at, redirect_uri, updated_at
        FROM `{PROJECT_ID}.{DATASET}.consents`
        WHERE consent_id = @consent_id
        ORDER BY updated_at DESC
        LIMIT 1
        """,
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("consent_id", "STRING", consent_id),
        ]),
    ).result())
    if not rows:
        return None
    consent = _clean(dict(rows[0]))
    _consent_cache[consent_id] = consent
    return dict(consent)


def save_consent(consent: dict) -> None:
    """Append consent state quickly and keep the single demo instance hot."""
    row = dict(consent)
    row["updated_at"] = datetime.now(timezone.utc).isoformat()
    table_id = f"{PROJECT_ID}.{DATASET}.consents"
    errors = _bq().insert_rows_json(table_id, [row])
    if errors:
        raise RuntimeError(f"Could not persist bank consent: {errors}")
    _consent_cache[row["consent_id"]] = row


def revoke_customer_consents(customer_id: str) -> int:
    """Append a Revoked version for every live consent held by a demo customer."""
    from google.cloud import bigquery

    rows = list(_bq().query(
        f"""
        SELECT * EXCEPT(row_num)
        FROM (
          SELECT consent_id, customer_id, bank_code, permissions, status,
                 created_at, expires_at, redirect_uri, updated_at,
                 ROW_NUMBER() OVER (PARTITION BY consent_id ORDER BY updated_at DESC) AS row_num
          FROM `{PROJECT_ID}.{DATASET}.consents`
          WHERE customer_id = @customer_id
        )
        WHERE row_num = 1 AND status NOT IN ('Revoked', 'Rejected', 'Expired')
        """,
        job_config=bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("customer_id", "STRING", customer_id),
        ]),
    ).result())
    for raw in rows:
        consent = _clean(dict(raw))
        consent["status"] = "Revoked"
        save_consent(consent)
    return len(rows)


def _ensure_fresh() -> None:
    """Reload the cores from BigQuery when the cache is older than the TTL."""
    if time.time() - _cache["loaded_at"] < CACHE_TTL_SECONDS and _cache["accounts"]:
        return
    client = _bq()

    def load(table: str) -> tuple[str, list[dict]]:
        rows = [dict(r) for r in client.query(
            f"SELECT * FROM `{PROJECT_ID}.{DATASET}.{table}`").result()]
        for row in rows:  # dates/timestamps -> ISO strings for JSON serialization
            for key, value in row.items():
                if hasattr(value, "isoformat"):
                    row[key] = value.isoformat()
        return table, rows

    with ThreadPoolExecutor(max_workers=3) as pool:
        for table, rows in pool.map(load, ("accounts", "transactions", "loans")):
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


def _clean(row: dict) -> dict:
    for key, value in row.items():
        if hasattr(value, "isoformat"):
            row[key] = value.isoformat()
    return row
