"""Additive runtime tables are prepared independently from demo seeding."""
from app.data import bigquery_client


def test_transaction_classification_table_is_created_if_missing(monkeypatch):
    created = []

    class FakeClient:
        def create_table(self, table, exists_ok=False):
            created.append((table, exists_ok))
            return table

        def query(self, sql):
            assert "ADD COLUMN IF NOT EXISTS seed_version" in sql

            class FinishedJob:
                @staticmethod
                def result():
                    return None

            return FinishedJob()

    monkeypatch.setattr(bigquery_client, "require_bigquery", lambda: None)
    monkeypatch.setattr(bigquery_client, "_client", lambda: FakeClient())
    monkeypatch.setattr(
        bigquery_client.config,
        "bq_table",
        lambda name: f"demo.edraak_finance.{name}",
    )
    bigquery_client._SCHEMAS.clear()
    bigquery_client._RUNTIME_TABLES_READY = False

    bigquery_client.ensure_runtime_tables()

    assert len(created) == 1
    table, exists_ok = created[0]
    assert table.full_table_id is None  # not sent to BigQuery in this unit test
    assert table.path.endswith("/tables/transaction_classifications")
    assert exists_ok is True
    assert [field.name for field in table.schema] == [
        "customer_id",
        "transaction_id",
        "category",
        "confidence",
        "classified_at",
    ]
