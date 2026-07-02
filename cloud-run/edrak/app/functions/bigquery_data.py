import os

from app.functions.mock_data import get_profiles, get_transactions_by_user


def _bigquery_config():
    return {
        "project_id": os.getenv("GCP_PROJECT_ID", ""),
        "dataset": os.getenv("BQ_DATASET", ""),
        "profiles_table": os.getenv("BQ_PROFILES_TABLE", ""),
        "transactions_table": os.getenv("BQ_TRANSACTIONS_TABLE", ""),
        "recommendations_table": os.getenv("BQ_RECOMMENDATIONS_TABLE", ""),
    }


def get_customer_profiles_from_bigquery():
    config = _bigquery_config()
    print(f"BigQuery profiles placeholder active. Config: {config}")
    return get_profiles()


def get_transactions_from_bigquery(user_id):
    config = _bigquery_config()
    print(f"BigQuery transactions placeholder active for {user_id}. Config: {config}")
    return get_transactions_by_user(user_id)


def save_recommendation_to_bigquery(payload):
    config = _bigquery_config()
    print(f"BigQuery recommendation save placeholder active. Config: {config}")
    print(f"Recommendation payload: {payload}")
    return {"saved": False, "mode": "mock"}
