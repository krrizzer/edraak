"""Seed the demo world: the banks' cores (bank_cores dataset) + Edraak's first-party data.

Residency (the whole open-banking story made physical):
  bank_cores dataset (the BANKS' world, served by the mock gateway API):
    - accounts / transactions / loans for ALL banks and customers
    - seed_meta: which day the synthetic world is anchored to
  edraak_finance dataset (Edraak's warehouse):
    - customers + each customer's HOST-bank rows only
    - everything else arrives via the consented gateway pull

AUTO-SEED: the backend calls ensure_fresh_seed() on startup. If seed_meta says the
world is anchored to a different day, everything regenerates anchored to today —
so a Cloud Run cold start on demo day gives fresh, correctly-dated data with no
manual step. Run manually only to force it:  python -m app.data.seed.load_seed_data
"""
import logging
from datetime import date, datetime, timezone

from app import config
from app.data.bigquery_client import require_bigquery
from app.data.seed.generate_seed_data import generate_all


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("edraak.seed")

CORE_TABLES = ["accounts", "transactions", "loans"]
# Edraak-side tables fully replaced by first-party generator output.
SOURCE_TABLES = ["customers", "accounts", "transactions", "loans"]
# Derived + pipeline tables cleared so nothing stale survives a reseed.
DERIVED_TABLES = ["user_profiles", "detected_obligations", "alerts",
                  "ob_consents", "ob_raw_payloads"]


def ensure_fresh_seed() -> bool:
    """Re-seed only when the world is anchored to a different day. Returns True if seeded."""
    require_bigquery()
    anchor = _current_anchor()
    today = date.today().isoformat()
    if anchor == today:
        logger.info("flow.seed.fresh anchor=%s message=Seed already anchored to today; skipping", anchor)
        return False
    logger.info("flow.seed.stale anchor=%s today=%s message=Re-seeding the demo world", anchor, today)
    load_seed_data()
    return True


def load_seed_data() -> None:
    """Generate demo rows relative to today and write both datasets."""
    require_bigquery()
    from google.cloud import bigquery

    client = bigquery.Client(project=config.gcp_project_id())
    tables = generate_all()
    first_party = _first_party_only(tables)

    # 1) The banks' world: full cross-bank rows behind the gateway.
    for name in CORE_TABLES:
        _replace(client, config.bq_core_table(name), tables[name])
    _replace(client, config.bq_core_table("seed_meta"),
             [{"anchor_date": date.today().isoformat(),
               "seeded_at": datetime.now(timezone.utc).isoformat()}])

    # 2) Edraak's warehouse: first-party rows only.
    for name in SOURCE_TABLES:
        _replace(client, config.bq_table(name), first_party[name])

    for name in DERIVED_TABLES:
        table_id = config.bq_table(name)
        try:
            client.query(f"TRUNCATE TABLE `{table_id}`").result()
        except Exception:
            # Rows streamed in the last ~90 minutes block TRUNCATE. Not fatal.
            logger.warning("flow.seed.truncate.skipped table=%s message=Streaming buffer likely active", name)

    logger.info("flow.seed.completed customers=%s core_transactions=%s host_transactions=%s",
                len(tables["customers"]), len(tables["transactions"]),
                len(first_party["transactions"]))


def _replace(client, table_id: str, rows: list[dict]) -> None:
    """Fully replace one table's contents via a truncating load job."""
    from google.cloud import bigquery

    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        schema=client.get_table(table_id).schema,
    )
    client.load_table_from_json(rows, table_id, job_config=job_config).result()
    logger.info("flow.seed.load.completed table=%s rows=%s", table_id, len(rows))


def _current_anchor() -> str | None:
    """Read the anchor date of the currently seeded world, if any."""
    from google.cloud import bigquery

    client = bigquery.Client(project=config.gcp_project_id())
    try:
        rows = list(client.query(
            f"SELECT anchor_date FROM `{config.bq_core_table('seed_meta')}` LIMIT 1").result())
        return rows[0]["anchor_date"].isoformat() if rows else None
    except Exception:
        logger.warning("flow.seed.meta_missing message=No seed_meta yet; will seed from scratch")
        return None


def _first_party_only(tables: dict) -> dict:
    """Keep customers, but restrict accounts/transactions/loans to each customer's host bank."""
    primary_bank = {
        a["customer_id"]: a["bank_code"]
        for a in tables["accounts"] if a.get("is_primary")
    }
    return {
        "customers": tables["customers"],
        "accounts": [a for a in tables["accounts"] if a["bank_code"] == primary_bank.get(a["customer_id"])],
        "transactions": [t for t in tables["transactions"] if t["bank_code"] == primary_bank.get(t["customer_id"])],
        "loans": [l for l in tables["loans"] if l["bank_code"] == primary_bank.get(l["customer_id"])],
    }


if __name__ == "__main__":
    load_seed_data()
