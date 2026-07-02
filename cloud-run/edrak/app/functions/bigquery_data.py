import os

from app.functions.load_user_profiles import load_all_user_profiles
from app.functions.mock_data import (
    get_active_loans_by_customer,
    get_customer_by_id,
    get_customer_by_username,
    get_transactions_by_customer,
    get_user_profile,
    save_user_profile,
)


def _bigquery_config():
    return {
        "project_id": os.getenv("GCP_PROJECT_ID", ""),
        "dataset": os.getenv("BQ_DATASET", ""),
        "customers_table": os.getenv("BQ_CUSTOMERS_TABLE", "customers"),
        "transactions_table": os.getenv("BQ_TRANSACTIONS_TABLE", "transactions"),
        "loans_table": os.getenv("BQ_LOANS_TABLE", "loans"),
        "user_profiles_table": os.getenv("BQ_USER_PROFILES_TABLE", "user_profiles"),
        "decision_requests_table": os.getenv("BQ_DECISION_REQUESTS_TABLE", "decision_requests"),
        "recommendations_table": os.getenv("BQ_RECOMMENDATIONS_TABLE", "recommendations"),
    }


def get_customer_by_username_from_bigquery(username):
    print(f"BigQuery customer username placeholder active. Config: {_bigquery_config()}")
    return get_customer_by_username(username)


def get_customer_by_id_from_bigquery(customer_id):
    print(f"BigQuery customer id placeholder active. Config: {_bigquery_config()}")
    return get_customer_by_id(customer_id)


def get_transactions_from_bigquery(customer_id):
    print(f"BigQuery transactions placeholder active for {customer_id}. Config: {_bigquery_config()}")
    return get_transactions_by_customer(customer_id)


def get_loans_from_bigquery(customer_id):
    print(f"BigQuery loans placeholder active for {customer_id}. Config: {_bigquery_config()}")
    return get_active_loans_by_customer(customer_id)


def load_user_profiles_to_bigquery(profiles=None):
    print(f"BigQuery user profile load placeholder active. Config: {_bigquery_config()}")
    return {"saved": False, "mode": "mock", "profiles_loaded": len(profiles or [])}


def get_user_profile_from_bigquery(customer_id):
    print(f"BigQuery user profile placeholder active for {customer_id}. Config: {_bigquery_config()}")
    profile = get_user_profile(customer_id)
    if profile:
        return profile

    profiles = load_all_user_profiles()
    for generated_profile in profiles:
        save_user_profile(generated_profile)
    return get_user_profile(customer_id)


def save_decision_request_to_bigquery(payload):
    print(f"BigQuery decision request save placeholder active. Config: {_bigquery_config()}")
    print(f"Decision request payload: {payload}")
    return {"saved": False, "mode": "mock"}


def save_recommendation_to_bigquery(payload):
    print(f"BigQuery recommendation save placeholder active. Config: {_bigquery_config()}")
    print(f"Recommendation payload: {payload}")
    return {"saved": False, "mode": "mock"}
