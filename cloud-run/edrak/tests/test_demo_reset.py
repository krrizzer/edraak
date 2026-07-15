"""The presentation reset must restore only the selected user's first-party rows."""
from datetime import date

import pytest

from app.data.seed import load_seed_data as seed_loader


def _world():
    return {
        "customers": [
            {"customer_id": "C1"},
            {"customer_id": "C2"},
        ],
        "accounts": [
            {"customer_id": "C1", "bank_code": "ALINMA", "is_primary": True},
            {"customer_id": "C1", "bank_code": "SNB", "is_primary": False},
            {"customer_id": "C2", "bank_code": "ALINMA", "is_primary": True},
        ],
        "transactions": [
            {"customer_id": "C1", "bank_code": "ALINMA"},
            {"customer_id": "C1", "bank_code": "SNB"},
            {"customer_id": "C2", "bank_code": "ALINMA"},
        ],
        "loans": [
            {"customer_id": "C1", "bank_code": "ALINMA"},
            {"customer_id": "C1", "bank_code": "SNB"},
        ],
    }


def test_reset_restores_only_selected_customer_host_bank(monkeypatch):
    captured = {}
    monkeypatch.setattr(seed_loader, "require_bigquery", lambda: None)
    monkeypatch.setattr(seed_loader, "generate_all", _world)
    monkeypatch.setattr(
        seed_loader,
        "reset_customer_data",
        lambda customer_id, rows: captured.update(customer_id=customer_id, rows=rows),
    )

    result = seed_loader.reset_demo_customer("C1")

    assert captured["customer_id"] == "C1"
    assert {row["bank_code"] for row in captured["rows"]["accounts"]} == {"ALINMA"}
    assert {row["bank_code"] for row in captured["rows"]["transactions"]} == {"ALINMA"}
    assert {row["bank_code"] for row in captured["rows"]["loans"]} == {"ALINMA"}
    assert result == {"customer_id": "C1", "accounts": 1, "transactions": 1, "loans": 1}


def test_reset_rejects_unknown_demo_customer(monkeypatch):
    monkeypatch.setattr(seed_loader, "require_bigquery", lambda: None)
    monkeypatch.setattr(seed_loader, "generate_all", _world)

    with pytest.raises(LookupError):
        seed_loader.reset_demo_customer("UNKNOWN")


def test_fresh_seed_requires_current_date_and_layout_version(monkeypatch):
    loaded = []
    monkeypatch.setattr(seed_loader, "require_bigquery", lambda: None)
    monkeypatch.setattr(seed_loader, "ensure_runtime_tables", lambda: None)
    monkeypatch.setattr(
        seed_loader,
        "_current_seed_state",
        lambda: (date.today().isoformat(), seed_loader.SEED_VERSION),
    )
    monkeypatch.setattr(seed_loader, "load_seed_data", lambda: loaded.append(True))

    assert seed_loader.ensure_fresh_seed() is False
    assert loaded == []


def test_same_day_old_layout_forces_reseed(monkeypatch):
    loaded = []
    monkeypatch.setattr(seed_loader, "require_bigquery", lambda: None)
    monkeypatch.setattr(seed_loader, "ensure_runtime_tables", lambda: None)
    monkeypatch.setattr(
        seed_loader,
        "_current_seed_state",
        lambda: (date.today().isoformat(), "older-layout"),
    )
    monkeypatch.setattr(seed_loader, "load_seed_data", lambda: loaded.append(True))

    assert seed_loader.ensure_fresh_seed() is True
    assert loaded == [True]


def test_seed_refresh_invalidates_gateway_cache(monkeypatch):
    captured = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(seed_loader.config, "openbanking_gateway_url", lambda: "http://gateway")
    monkeypatch.setattr(seed_loader.config, "demo_reset_token", lambda: "token")
    monkeypatch.setattr(
        seed_loader.urllib.request,
        "urlopen",
        lambda request, timeout: captured.append((request, timeout)) or Response(),
    )

    seed_loader._invalidate_gateway_cache()

    request, timeout = captured[0]
    assert request.full_url == "http://gateway/internal/core-cache/invalidate"
    assert request.method == "POST"
    assert request.headers["X-demo-reset-token"] == "token"
    assert timeout == 10
