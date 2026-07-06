import json
import logging
import os
from datetime import date, datetime
from uuid import uuid4


logger = logging.getLogger("edraak.bigquery")


def get_customer_by_username_from_bigquery(username):
    _require_bigquery()
    logger.info("bigquery.query.start table=customers lookup=username username=%s", username)
    return _query_one(
        f"""
        SELECT customer_id, username_en, ar_name, en_name, national_id, birthday,
               salary, current_balance, city, employment_sector, employer_name,
               account_open_date, created_at
        FROM `{_table("customers")}`
        WHERE LOWER(username_en) = @username
        LIMIT 1
        """,
        [("username", username.strip().lower())],
        "customers",
    )


def get_customer_by_id_from_bigquery(customer_id):
    _require_bigquery()
    logger.info("bigquery.query.start table=customers lookup=customer_id customer_id=%s", customer_id)
    return _query_one(
        f"""
        SELECT customer_id, username_en, ar_name, en_name, national_id, birthday,
               salary, current_balance, city, employment_sector, employer_name,
               account_open_date, created_at
        FROM `{_table("customers")}`
        WHERE customer_id = @customer_id
        LIMIT 1
        """,
        [("customer_id", customer_id)],
        "customers",
    )


def list_customers_from_bigquery(customer_id=None):
    _require_bigquery()
    if customer_id:
        logger.info("flow.data.bigquery step=customers action=load_one customer_id=%s message=Loading one customer for profile generation", customer_id)
        customer = get_customer_by_id_from_bigquery(customer_id)
        return [customer] if customer else []

    logger.info("flow.data.bigquery step=customers action=load_all message=Loading all customers for profile generation")
    return _query_many(
        f"""
        SELECT customer_id, username_en, ar_name, en_name, national_id, birthday,
               salary, current_balance, city, employment_sector, employer_name,
               account_open_date, created_at
        FROM `{_table("customers")}`
        ORDER BY customer_id
        """,
        [],
        "customers",
    )


def get_transactions_from_bigquery(customer_id):
    _require_bigquery()
    logger.info("bigquery.query.start table=transactions customer_id=%s", customer_id)
    return _query_many(
        f"""
        SELECT transaction_id, customer_id, transaction_date, merchant, category,
               amount, transaction_type, is_recurring, channel, created_at
        FROM `{_table("transactions")}`
        WHERE customer_id = @customer_id
        ORDER BY transaction_date DESC
        """,
        [("customer_id", customer_id)],
        "transactions",
    )


def get_loans_from_bigquery(customer_id):
    _require_bigquery()
    logger.info("bigquery.query.start table=loans customer_id=%s", customer_id)
    return _query_many(
        f"""
        SELECT loan_id, customer_id, loan_type, loan_total_amount, total_profit_amount,
               total_amount, remaining_amount, monthly_installment, start_date,
               end_date, status, created_at
        FROM `{_table("loans")}`
        WHERE customer_id = @customer_id
          AND status = 'active'
        ORDER BY start_date DESC
        """,
        [("customer_id", customer_id)],
        "loans",
    )


def get_user_profile_from_bigquery(customer_id):
    _require_bigquery()
    logger.info("bigquery.query.start table=user_profiles customer_id=%s", customer_id)
    return _query_one(
        f"""
        SELECT customer_id, ar_name, en_name, salary, current_balance,
               active_loans_count, total_remaining_loans, monthly_loan_installments,
               avg_monthly_spending, avg_flexible_spending, recurring_obligations,
               savings_estimate, obligation_ratio, spending_behavior_summary_ar,
               risk_preference_estimate_ar, profile_generated_at
        FROM `{_table("user_profiles")}`
        WHERE customer_id = @customer_id
        ORDER BY profile_generated_at DESC
        LIMIT 1
        """,
        [("customer_id", customer_id)],
        "user_profiles",
    )


def save_decision_request_to_bigquery(payload):
    _require_bigquery()
    row = dict(payload)
    row.setdefault("request_id", f"REQ-{uuid4().hex[:12]}")
    row.setdefault("created_at", datetime.utcnow().isoformat())
    _insert_rows("decision_requests", [row])
    return {"saved": True, "mode": "bigquery", "request_id": row["request_id"]}


def save_recommendation_to_bigquery(payload):
    _require_bigquery()
    row = {
        "recommendation_id": f"REC-{uuid4().hex[:12]}",
        "request_id": payload.get("request_id"),
        "customer_id": payload["customer"]["customer_id"],
        "recommendation": payload["recommendation"],
        "risk_score": payload["risk_score"],
        "safety_score": payload["safety_score"],
        "obligation_ratio_before": payload["obligation_ratio_before"],
        "obligation_ratio_after": payload["obligation_ratio_after"],
        "monthly_buffer_after": payload["monthly_buffer_after"],
        "financial_seatbelt_status": payload["financial_seatbelt_status"],
        "confidence": payload["confidence"],
        "validation_warnings_json": _safe_json(payload["validation_warnings_ar"]),
        "explanation_ar": payload["explanation_ar"],
        "risk_factors_json": _safe_json(payload["risk_factors_ar"]),
        "safer_options_json": _safe_json(payload["safer_options_ar"]),
        "readiness_path_json": _safe_json(payload["readiness_path_ar"]),
        "agent_trace_json": _safe_json(payload["agent_trace_ar"]),
        "created_at": datetime.utcnow().isoformat(),
    }
    _insert_rows("recommendations", [row])
    return {"saved": True, "mode": "bigquery", "recommendation_id": row["recommendation_id"]}


def save_user_profile_to_bigquery(profile):
    _require_bigquery()
    _insert_rows("user_profiles", [profile])
    return {"saved": True, "mode": "bigquery", "customer_id": profile["customer_id"]}


def _require_bigquery():
    if os.getenv("USE_BIGQUERY", "true").lower() != "true":
        raise RuntimeError("USE_BIGQUERY must be true. Production mode does not use mock data.")

    project_id = os.getenv("GCP_PROJECT_ID", "")
    if not project_id or project_id == "YOUR_PROJECT_ID":
        raise RuntimeError("GCP_PROJECT_ID is required for BigQuery production mode.")


def _config():
    return {
        "project_id": os.getenv("GCP_PROJECT_ID", ""),
        "dataset": os.getenv("BQ_DATASET", "edraak_finance"),
        "customers": os.getenv("BQ_CUSTOMERS_TABLE", "customers"),
        "transactions": os.getenv("BQ_TRANSACTIONS_TABLE", "transactions"),
        "loans": os.getenv("BQ_LOANS_TABLE", "loans"),
        "user_profiles": os.getenv("BQ_USER_PROFILES_TABLE", "user_profiles"),
        "decision_requests": os.getenv("BQ_DECISION_REQUESTS_TABLE", "decision_requests"),
        "recommendations": os.getenv("BQ_RECOMMENDATIONS_TABLE", "recommendations"),
    }


def _table(name):
    config = _config()
    return f"{config['project_id']}.{config['dataset']}.{config[name]}"


def _client():
    from google.cloud import bigquery

    return bigquery.Client(project=_config()["project_id"])


def _query_one(sql, params, table_name):
    rows = _query_many(sql, params, table_name)
    if rows:
        logger.info("bigquery.query_one.success table=%s rows=1", table_name)
        return rows[0]
    logger.info("bigquery.query_one.empty table=%s", table_name)
    return None


def _query_many(sql, params, table_name):
    try:
        from google.cloud import bigquery

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter(name, "STRING", value)
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


def _insert_rows(table_name, rows):
    table_id = _table(table_name)
    try:
        errors = _client().insert_rows_json(table_id, rows)
    except Exception:
        logger.exception("bigquery.insert.failed table=%s", table_name)
        raise RuntimeError(f"BigQuery insert failed for {table_name}.")

    if errors:
        logger.error("bigquery.insert.errors table=%s errors=%s", table_name, _safe_json(errors))
        raise RuntimeError(f"BigQuery insert failed for {table_name}: {_safe_json(errors)}")

    logger.info("bigquery.insert.success table=%s rows=%s", table_name, len(rows))


def _clean_row(row):
    return {key: _clean_value(value) for key, value in row.items()}


def _clean_value(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _safe_json(payload):
    return json.dumps(payload, ensure_ascii=True, default=str)
