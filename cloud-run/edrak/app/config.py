"""Environment configuration in one place: env vars, table names, and file paths."""
import os
from pathlib import Path


def _env(name: str, default: str = "") -> str:
    """Read one environment variable with a default."""
    return os.getenv(name, default)


def gcp_project_id() -> str:
    """Return the Google Cloud project id required for BigQuery and Vertex AI."""
    return _env("GCP_PROJECT_ID", "")


def bq_dataset() -> str:
    """Return the BigQuery dataset that holds all Edraak tables."""
    return _env("BQ_DATASET", "edraak_finance")


def bq_table(name: str) -> str:
    """Return the fully qualified BigQuery table id for a logical table name."""
    tables = {
        "customers": _env("BQ_CUSTOMERS_TABLE", "customers"),
        "accounts": _env("BQ_ACCOUNTS_TABLE", "accounts"),
        "transactions": _env("BQ_TRANSACTIONS_TABLE", "transactions"),
        "loans": _env("BQ_LOANS_TABLE", "loans"),
        "user_profiles": _env("BQ_USER_PROFILES_TABLE", "user_profiles"),
        "detected_obligations": _env("BQ_DETECTED_OBLIGATIONS_TABLE", "detected_obligations"),
        "alerts": _env("BQ_ALERTS_TABLE", "alerts"),
        "decision_requests": _env("BQ_DECISION_REQUESTS_TABLE", "decision_requests"),
        "recommendations": _env("BQ_RECOMMENDATIONS_TABLE", "recommendations"),
    }
    return f"{gcp_project_id()}.{bq_dataset()}.{tables[name]}"


def use_bigquery() -> bool:
    """Return True when BigQuery is the data source (the only supported mode)."""
    return _env("USE_BIGQUERY", "true").lower() == "true"


def use_gemini() -> bool:
    """Return True when Vertex AI Gemini agents are enabled (the only supported mode)."""
    return _env("USE_GEMINI", "true").lower() == "true"


def vertex_location() -> str:
    """Return the Vertex AI location for Gemini calls."""
    return _env("VERTEX_LOCATION", "global")


def gemini_model() -> str:
    """Return the Gemini model id used by every agent."""
    return _env("GEMINI_MODEL", "gemini-2.5-flash-lite")


def risk_model_path() -> Path:
    """Return the joblib file path of the trained risk model."""
    default = Path(__file__).parent / "functions" / "models" / "risk_model.joblib"
    return Path(_env("RISK_MODEL_PATH", str(default)))


# How long a detected_obligations cache row stays fresh before the
# Transaction Intelligence Agent must re-classify the raw transactions.
OBLIGATION_CACHE_MAX_AGE_HOURS = int(_env("OBLIGATION_CACHE_MAX_AGE_HOURS", "24"))
