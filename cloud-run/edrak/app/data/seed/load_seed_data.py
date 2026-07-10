"""Load generated seed data into BigQuery, replacing previous demo rows.

Run from cloud-run/edrak with:  python -m app.data.seed.load_seed_data
"""
import logging

from app import config
from app.data.bigquery_client import require_bigquery
from app.data.seed.generate_seed_data import generate_all


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("edraak.seed")

# Source tables are fully replaced by the generator output.
SOURCE_TABLES = ["customers", "accounts", "transactions", "loans"]
# Derived tables are cleared so stale caches never survive a reseed.
DERIVED_TABLES = ["user_profiles", "detected_obligations", "alerts"]


def load_seed_data() -> None:
    """Generate demo rows relative to today and write them to BigQuery."""
    require_bigquery()
    from google.cloud import bigquery

    client = bigquery.Client(project=config.gcp_project_id())
    tables = generate_all()

    for name in SOURCE_TABLES:
        rows = tables[name]
        table_id = config.bq_table(name)
        logger.info("flow.seed.load.start table=%s rows=%s message=Replacing table contents", name, len(rows))
        # Load jobs (not streaming inserts) so reseeding fully replaces old rows.
        job_config = bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            schema=client.get_table(table_id).schema,
        )
        client.load_table_from_json(rows, table_id, job_config=job_config).result()
        logger.info("flow.seed.load.completed table=%s rows=%s", name, len(rows))

    for name in DERIVED_TABLES:
        table_id = config.bq_table(name)
        logger.info("flow.seed.truncate.start table=%s message=Clearing derived table", name)
        client.query(f"TRUNCATE TABLE `{table_id}`").result()
        logger.info("flow.seed.truncate.completed table=%s", name)

    logger.info("flow.seed.completed customers=%s transactions=%s loans=%s accounts=%s",
                len(tables["customers"]), len(tables["transactions"]),
                len(tables["loans"]), len(tables["accounts"]))


if __name__ == "__main__":
    load_seed_data()
