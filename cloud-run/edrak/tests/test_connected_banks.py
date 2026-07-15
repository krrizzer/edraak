from app.data import bigquery_client


def test_authorised_empty_bank_is_still_connected(monkeypatch):
    captured = {}

    def fake_query(sql, params, table_name):
        captured["sql"] = sql
        captured["params"] = params
        captured["table_name"] = table_name
        return [{"bank_code": "ALINMA"}, {"bank_code": "SNB"}]

    monkeypatch.setattr(bigquery_client, "_query_many", fake_query)

    assert bigquery_client.get_connected_banks("CUST001") == ["ALINMA", "SNB"]
    assert "ob_consents" in captured["sql"]
    assert "status = 'Authorised'" in captured["sql"]
    assert captured["params"] == [("customer_id", "CUST001")]

