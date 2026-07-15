"""Seed the demo world: the banks' cores (bank_cores dataset) + Edraak's first-party data.

Residency (the whole open-banking story made physical):
  bank_cores dataset (the BANKS' world, served by the mock gateway API):
    - accounts / transactions / loans for ALL banks and customers
    - seed_meta: which day and generator-layout version the world uses
  edraak_finance dataset (Edraak's warehouse):
    - customers + each customer's HOST-bank rows only
    - everything else arrives via the consented gateway pull

AUTO-SEED: the backend calls ensure_fresh_seed() on startup. If seed_meta says the
world uses a different day or generator-layout version, everything regenerates
anchored to today. Run manually only to force it:
python -m app.data.seed.load_seed_data
"""
import logging
import json
import urllib.request
from datetime import date, datetime, timezone

from app import config
from app.data.bigquery_client import ensure_runtime_tables, require_bigquery, reset_customer_data
from app.data.seed.generate_seed_data import generate_all


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("edraak.seed")

CORE_TABLES = ["accounts", "transactions", "loans"]
# Edraak-side tables fully replaced by first-party generator output.
SOURCE_TABLES = ["customers", "accounts", "transactions", "loans"]
# Derived + pipeline tables cleared so nothing stale survives a reseed.
DERIVED_TABLES = [
    "user_profiles", "detected_obligations", "transaction_classifications",
    "alerts", "ob_consents", "ob_raw_payloads", "decision_requests",
    "recommendations",
]

# Bump this whenever generated row placement or scenario semantics change.
# Date freshness alone cannot detect a code update made later on the same day.
SEED_VERSION = "2026-07-five-realistic-personas-v2"


def ensure_fresh_seed() -> bool:
    """Re-seed when either the date or generated-data layout is stale."""
    require_bigquery()
    ensure_runtime_tables()
    anchor, version = _current_seed_state()
    today = date.today().isoformat()
    if anchor == today and version == SEED_VERSION:
        logger.info(
            "flow.seed.fresh anchor=%s version=%s message=Seed date and layout are current; skipping",
            anchor, version,
        )
        return False
    logger.info(
        "flow.seed.stale anchor=%s today=%s version=%s expected_version=%s message=Re-seeding the demo world",
        anchor, today, version, SEED_VERSION,
    )
    load_seed_data()
    return True


def load_seed_data() -> None:
    """Generate demo rows relative to today and write both datasets."""
    require_bigquery()
    ensure_runtime_tables()
    from google.cloud import bigquery

    client = bigquery.Client(project=config.gcp_project_id())
    tables = generate_all()
    first_party = _first_party_only(tables)

    # 1) The banks' world: full cross-bank rows behind the gateway.
    for name in CORE_TABLES:
        _replace(client, config.bq_core_table(name), tables[name])
    # A new demo day starts with no old bank approvals. Same-day Cloud Run
    # restarts skip seeding, so consents remain durable during the presentation.
    try:
        client.query(f"TRUNCATE TABLE `{config.bq_core_table('consents')}`").result()
    except Exception:
        # A same-day layout migration may find recently streamed consent rows.
        # They expire or can be reset separately; never block core-data refresh.
        logger.warning(
            "flow.seed.truncate.skipped table=bank_cores.consents "
            "message=Recent consent rows are still in the streaming buffer"
        )
    _replace(client, config.bq_core_table("seed_meta"),
             [{"anchor_date": date.today().isoformat(),
               "seeded_at": datetime.now(timezone.utc).isoformat(),
               "seed_version": SEED_VERSION}])

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

    _invalidate_gateway_cache()

    logger.info("flow.seed.completed customers=%s core_transactions=%s host_transactions=%s",
                len(tables["customers"]), len(tables["transactions"]),
                len(first_party["transactions"]))


def _invalidate_gateway_cache() -> None:
    """Make the separate gateway observe replaced bank cores immediately."""
    request = urllib.request.Request(
        f"{config.openbanking_gateway_url()}/internal/core-cache/invalidate",
        data=json.dumps({}).encode(),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "x-demo-reset-token": config.demo_reset_token(),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=10):
            pass
        logger.info("flow.seed.gateway_cache_invalidated")
    except Exception:
        # The gateway can be started after the backend in local development.
        # Its cache is empty on startup and otherwise expires by TTL.
        logger.warning(
            "flow.seed.gateway_cache_invalidation_skipped "
            "message=Gateway unavailable; cache will refresh on startup or TTL"
        )


def reset_demo_customer(customer_id: str) -> dict:
    """Restore one known demo customer to the clean, host-bank-only starting state."""
    require_bigquery()
    tables = generate_all()
    if not any(row["customer_id"] == customer_id for row in tables["customers"]):
        raise LookupError(customer_id)

    first_party = _first_party_only(tables)
    customer_rows = {
        name: [row for row in first_party[name] if row["customer_id"] == customer_id]
        for name in ("accounts", "transactions", "loans")
    }
    reset_customer_data(customer_id, customer_rows)
    logger.info("flow.demo_reset.customer_restored customer_id=%s", customer_id)
    return {
        "customer_id": customer_id,
        "accounts": len(customer_rows["accounts"]),
        "transactions": len(customer_rows["transactions"]),
        "loans": len(customer_rows["loans"]),
    }


def _replace(client, table_id: str, rows: list[dict]) -> None:
    """Fully replace one table's contents via a truncating load job."""
    from google.cloud import bigquery

    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        schema=client.get_table(table_id).schema,
    )
    client.load_table_from_json(rows, table_id, job_config=job_config).result()
    logger.info("flow.seed.load.completed table=%s rows=%s", table_id, len(rows))


def _current_seed_state() -> tuple[str | None, str | None]:
    """Read the date and generator-layout version of the current demo world."""
    from google.cloud import bigquery

    client = bigquery.Client(project=config.gcp_project_id())
    try:
        rows = list(client.query(
            f"SELECT anchor_date, seed_version "
            f"FROM `{config.bq_core_table('seed_meta')}` LIMIT 1").result())
        if not rows:
            return None, None
        return rows[0]["anchor_date"].isoformat(), rows[0].get("seed_version")
    except Exception:
        logger.warning("flow.seed.meta_missing message=No seed_meta yet; will seed from scratch")
        return None, None


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
