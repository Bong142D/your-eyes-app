import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app as billing_app  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test_billing.db")
    monkeypatch.setenv("BILLING_DB_PATH", db_path)
    monkeypatch.setenv("BILLING_ENV", "dev")
    return billing_app.app.test_client()