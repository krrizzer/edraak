"""All BigQuery reads and writes for the Edraak backend in one place."""
import json
import logging
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from app import config


logger = logging.getLogger("edraak.bigquery")


def get_customer_by_username(username: str) -> dict | None:
    """Find one customer row by the English login username."""
    logger.info("bigquery.query.start table=customers lookup=username username=%s", username)
    return _query_one(
        f"""
        SELECT customer_id, username_en, ar_name, en_name, national_id, birthday,
               salary, city, employment_sector, employer_name, account_open_date, created_at
        FROM `{config.bq_table("customers")}`
        WHERE LOWER(username_en) = @username
        LIMIT 1
        """,
        [("username", username.strip().lower())],
        "customers",
    )


def get_customer_by_id(customer_id: str) -> dict | None:
    """Find one customer row by customer_id."""
    logger.info("bigquery.query.start table=customers lookup=customer_id customer_id=%s", customer_id)
    return _query_one(
        f"""
        SELECT customer_id, username_en, ar_name, en_name, national_id, birthday,
               salary, city, employment_sector, employer_name, account_open_date, created_at
        FROM `{config.bq_table("customers")}`
        WHERE customer_id = @customer_id
        LIMIT 1
        """,
        [("customer_id", customer_id)],
        "customers",
    )


def get_accounts(customer_id: str) -> list[dict]:
    """Load every bank account the customer holds across all banks."""
    logger.info("bigquery.query.start table=accounts customer_id=%s", customer_id)
    return _query_many(
        f"""
        SELECT account_id, customer_id, bank_code, bank_name_ar, account_type,
               iban, balance, is_primary, created_at
        FROM `{config.bq_table("accounts")}`
        WHERE customer_id = @customer_id
        ORDER BY is_primary DESC, bank_code
        """,
        [("customer_id", customer_id)],
        "accounts",
    )


def get_transactions(customer_id: str) -> list[dict]:
    """Load the cross-bank transaction history, newest first."""
    logger.info("bigquery.query.start table=transactions customer_id=%s", customer_id)
    return _query_many(
        f"""
        SELECT transaction_id, customer_id, account_id, bank_code, transaction_date,
               merchant, category, raw_description, amount, transaction_type, channel, created_at
        FROM `{config.bq_table("transactions")}`
        WHERE customer_id = @customer_id
        ORDER BY transaction_date DESC
        """,
        [("customer_id", customer_id)],
        "transactions",
    )


def get_loans(customer_id: str) -> list[dict]:
    """Load active loans across all banks, including remaining_months."""
    logger.info("bigquery.query.start table=loans customer_id=%s", customer_id)
    return _query_many(
        f"""
        SELECT loan_id, customer_id, bank_code, loan_type, loan_total_amount,
               total_profit_amount, total_amount, remaining_amount, monthly_installment,
               remaining_months, first_installment_date, start_date, end_date, status, created_at
        FROM `{config.bq_table("loans")}`
        WHERE customer_id = @customer_id
          AND status = 'active'
        ORDER BY start_date DESC
        """,
        [("customer_id", customer_id)],
        "loans",
    )


def get_user_profile(customer_id: str) -> dict | None:
    """Load the latest derived cross-bank profile row, if one exists."""
    logger.info("bigquery.query.start table=user_profiles customer_id=%s", customer_id)
    return _query_one(
        f"""
        SELECT customer_id, ar_name, en_name, salary, salary_day, salary_timing_variance_days,
               total_balance, banks_count, active_loans_count, total_remaining_loans,
               monthly_loan_installments, avg_monthly_spending, avg_flexible_spending,
               monthly_spending_std, profile_generated_at
        FROM `{config.bq_table("user_profiles")}`
        WHERE customer_id = @customer_id
        ORDER BY profile_generated_at DESC
        LIMIT 1
        """,
        [("customer_id", customer_id)],
        "user_profiles",
    )


def save_user_profile(profile: dict) -> None:
    """Store one derived cross-bank profile row."""
    _insert_rows("user_profiles", [profile])


def get_fresh_detected_obligations(customer_id: str) -> list[dict]:
    """Load the newest detected_obligations batch if it is younger than the cache limit."""
    logger.info("bigquery.query.start table=detected_obligations customer_id=%s", customer_id)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=config.OBLIGATION_CACHE_MAX_AGE_HOURS)
    return _query_many(
        f"""
        SELECT customer_id, obligation_type, counterparty, monthly_amount, day_of_month,
               remaining_months, confidence, is_committed, source_bank_codes, detected_at
        FROM `{config.bq_table("detected_obligations")}`
        WHERE customer_id = @customer_id
          AND detected_at = (
            SELECT MAX(detected_at)
            FROM `{config.bq_table("detected_obligations")}`
            WHERE customer_id = @customer_id
          )
          AND detected_at >= @cutoff
        """,
        [("customer_id", customer_id), ("cutoff", cutoff.isoformat())],
        "detected_obligations",
        param_types={"cutoff": "TIMESTAMP"},
    )


def save_detected_obligations(customer_id: str, obligations: list[dict]) -> None:
    """Store one batch of Transaction Intelligence output as the new cache.

    Written with a LOAD JOB (not streaming) so clear_detected_obligations can
    DELETE these rows immediately — streaming-buffered rows can't be deleted.
    """
    detected_at = datetime.now(timezone.utc).isoformat()
    rows = [
        {
            "customer_id": customer_id,
            "obligation_type": item["obligation_type"],
            "counterparty": item["counterparty"],
            "monthly_amount": item["monthly_amount"],
            "day_of_month": item["day_of_month"],
            "remaining_months": item.get("remaining_months"),
            "confidence": item["confidence"],
            "is_committed": item["is_committed"],
            "source_bank_codes": item.get("source_bank_codes", []),
            "detected_at": detected_at,
        }
        for item in obligations
    ]
    if rows:
        _load_rows("detected_obligations", rows).result()


def clear_detected_obligations(customer_id: str) -> None:
    """Invalidate the obligations cache — required after ingesting a new bank,
    or the analyzer would keep reusing a classification that never saw it."""
    require_bigquery()
    _client().query(
        f"DELETE FROM `{config.bq_table('detected_obligations')}` WHERE customer_id = @customer_id",
        job_config=_scalar_params([("customer_id", customer_id)]),
    ).result()
    logger.info("flow.ingest.obligations_cache.cleared customer_id=%s", customer_id)


def save_decision_request(payload: dict) -> str:
    """Store one decision request row (storage-only table). Returns request_id."""
    row = dict(payload)
    row.setdefault("request_id", f"REQ-{uuid4().hex[:12]}")
    row.setdefault("created_at", datetime.now(timezone.utc).isoformat())
    _insert_rows("decision_requests", [row])
    return row["request_id"]


def save_recommendation(payload: dict) -> str:
    """Store one recommendation row shaped for the reshaped schema (storage-only table)."""
    forecast = payload["forecast"]
    row = {
        "recommendation_id": f"REC-{uuid4().hex[:12]}",
        "request_id": payload.get("request_id"),
        "customer_id": payload["customer"]["customer_id"],
        "recommendation": payload["recommendation"],
        "ready_in_months": payload.get("ready_in_months"),
        "risk_probability": payload["risk_probability"],
        "obligation_ratio_now": forecast["obligation_ratio_now"],
        "obligation_ratio_peak": forecast["obligation_ratio_peak"],
        "first_shortfall_month": forecast.get("first_shortfall_month"),
        "first_shortfall_amount": forecast.get("first_shortfall_amount"),
        "min_buffer_value": forecast["min_buffer_value"],
        "months_of_savings_cover": forecast["months_of_savings_cover"],
        "forecast_json": _safe_json(forecast),
        "validation_warnings_json": _safe_json(payload["validation_warnings_ar"]),
        "explanation_ar": payload["explanation_ar"],
        "risk_factors_json": _safe_json(payload["risk_factors_ar"]),
        "safer_options_json": _safe_json(payload["safer_options_ar"]),
        "step_trace_json": _safe_json(payload["step_trace"]),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _insert_rows("recommendations", [row])
    return row["recommendation_id"]


def save_alert(alert: dict) -> str:
    """Store one radar alert row (storage-only table). Returns alert_id."""
    row = dict(alert)
    row.setdefault("alert_id", f"ALR-{uuid4().hex[:12]}")
    row.setdefault("created_at", datetime.now(timezone.utc).isoformat())
    _insert_rows("alerts", [row])
    return row["alert_id"]


def get_alerts(customer_id: str) -> list[dict]:
    """List stored radar alerts for the UI, newest first. Agents never read this."""
    logger.info("bigquery.query.start table=alerts customer_id=%s", customer_id)
    return _query_many(
        f"""
        SELECT alert_id, customer_id, created_at, alert_type, gap_amount, gap_date,
               cause_category, message_ar, trajectory_json
        FROM `{config.bq_table("alerts")}`
        WHERE customer_id = @customer_id
        ORDER BY created_at DESC
        LIMIT 20
        """,
        [("customer_id", customer_id)],
        "alerts",
    )


def get_connected_banks(customer_id: str) -> list[str]:
    """Distinct bank codes we currently hold data for (host bank + any ingested banks)."""
    rows = _query_many(
        f"""
        SELECT DISTINCT bank_code
        FROM `{config.bq_table("accounts")}`
        WHERE customer_id = @customer_id AND bank_code IS NOT NULL
        """,
        [("customer_id", customer_id)],
        "accounts",
    )
    return sorted(r["bank_code"] for r in rows if r.get("bank_code"))


def save_consent(consent: dict) -> None:
    """Record one consent in the TPP-side ledger."""
    _insert_rows("ob_consents", [consent])


def get_consents(customer_id: str) -> list[dict]:
    """List the customer's consents for the UI (linked accounts management)."""
    return _query_many(
        f"""
        SELECT consent_id, customer_id, bank_code, status, permissions,
               created_at, expires_at, revoked_at
        FROM `{config.bq_table("ob_consents")}`
        WHERE customer_id = @customer_id
        ORDER BY created_at DESC
        """,
        [("customer_id", customer_id)],
        "ob_consents",
    )


def save_raw_payloads(rows: list[dict]) -> None:
    """Land a batch of raw KSAOB payloads in the bronze layer, as received."""
    if rows:
        _insert_rows("ob_raw_payloads", rows)


def ingest_silver(customer_id: str, bank_code: str, tables: dict[str, list[dict]],
                  already_linked: bool) -> None:
    """Land one bank's pulled rows in the silver tables, fast.

    First link (the common case): the bank has no rows yet, so everything goes in
    via streaming inserts — sub-second, no DELETE needed. Re-link: delete the old
    rows first (one scripted job); if that fails because the previous rows are
    still in the streaming buffer, skip the rewrite — the generator is
    deterministic, so the rows already there are identical anyway.
    """
    require_bigquery()
    if already_linked:
        script = "\n".join(
            f"DELETE FROM `{config.bq_table(name)}` WHERE customer_id = @customer_id AND bank_code = @bank_code;"
            for name in tables
        )
        try:
            _client().query(script, job_config=_scalar_params(
                [("customer_id", customer_id), ("bank_code", bank_code)])).result()
        except Exception:
            logger.warning("flow.ingest.silver.rewrite_skipped customer_id=%s bank=%s message=Previous rows still in streaming buffer; identical data already present",
                           customer_id, bank_code)
            return
    for name, rows in tables.items():
        if rows:
            _insert_rows(name, rows)
    logger.info("flow.ingest.silver.landed customer_id=%s bank=%s relinked=%s",
                customer_id, bank_code, already_linked)


def _load_rows(table_name: str, rows: list[dict]) -> "object":
    """Start a load-job append (immediately deletable, unlike streaming). Returns the job."""
    from google.cloud import bigquery

    table_id = config.bq_table(table_name)
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        schema=_schema(table_id),
    )
    try:
        job = _client().load_table_from_json(rows, table_id, job_config=job_config)
    except Exception:
        logger.exception("bigquery.load.failed table=%s", table_name)
        raise RuntimeError(f"BigQuery load failed for {table_name}.")
    logger.info("bigquery.load.started table=%s rows=%s", table_name, len(rows))
    return job




def _scalar_params(params: list[tuple]):
    from google.cloud import bigquery

    return bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter(name, "STRING", value) for name, value in params
    ])


def require_bigquery() -> None:
    """Fail fast when BigQuery production mode is not configured."""
    if not config.use_bigquery():
        raise RuntimeError("USE_BIGQUERY must be true. Production mode does not use mock data.")
    if not config.gcp_project_id() or config.gcp_project_id() == "YOUR_PROJECT_ID":
        raise RuntimeError("GCP_PROJECT_ID is required for BigQuery production mode.")


# One client (and its auth handshake) per process — recreating it per query was
# costing seconds on every single call and dominated page-load and ingest times.
_CLIENT = None
_SCHEMAS: dict[str, list] = {}


def _client():
    global _CLIENT
    if _CLIENT is None:
        from google.cloud import bigquery

        _CLIENT = bigquery.Client(project=config.gcp_project_id())
    return _CLIENT


def _schema(table_id: str):
    """Cache table schemas — load jobs need them and they never change mid-run."""
    if table_id not in _SCHEMAS:
        _SCHEMAS[table_id] = _client().get_table(table_id).schema
    return _SCHEMAS[table_id]


def _query_one(sql: str, params: list[tuple], table_name: str) -> dict | None:
    rows = _query_many(sql, params, table_name)
    if rows:
        logger.info("bigquery.query_one.success table=%s rows=1", table_name)
        return rows[0]
    logger.info("bigquery.query_one.empty table=%s", table_name)
    return None


def _query_many(sql: str, params: list[tuple], table_name: str, param_types: dict | None = None) -> list[dict]:
    require_bigquery()
    try:
        from google.cloud import bigquery

        types = param_types or {}
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter(name, types.get(name, "STRING"), value)
                for name, value in params
            ]
        )
        rows = _client().query(sql, job_config=job_config).result()
    except Exception:
        logger.exception("bigquery.query.failed table=%s", table_name)
        raise RuntimeError(f"BigQuery query failed for {table_name}.")

    cleaned = [_clean_row(dict(row)) for row in rows]
    logger.info("bigquery.query.success table=%s rows=%s", table_name, len(cleaned))
    return cleaned


def _insert_rows(table_name: str, rows: list[dict]) -> None:
    require_bigquery()
    table_id = config.bq_table(table_name)
    try:
        errors = _client().insert_rows_json(table_id, rows)
    except Exception:
        logger.exception("bigquery.insert.failed table=%s", table_name)
        raise RuntimeError(f"BigQuery insert failed for {table_name}.")

    if errors:
        logger.error("bigquery.insert.errors table=%s errors=%s", table_name, _safe_json(errors))
        raise RuntimeError(f"BigQuery insert failed for {table_name}: {_safe_json(errors)}")

    logger.info("bigquery.insert.success table=%s rows=%s", table_name, len(rows))


def _clean_row(row: dict) -> dict:
    return {key: _clean_value(value) for key, value in row.items()}


def _clean_value(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _safe_json(payload) -> str:
    return json.dumps(payload, ensure_ascii=True, default=str)
