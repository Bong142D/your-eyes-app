import sqlite3
import uuid
from datetime import datetime, timedelta

from tiers import DEFAULT_TIER

SCHEMA_PATH = __file__.replace("models.py", "schema.sql")


def _connect(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path):
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = f.read()
    conn = _connect(db_path)
    try:
        conn.executescript(schema)
        conn.commit()
    finally:
        conn.close()


def create_account(db_path, email):
    conn = _connect(db_path)
    try:
        existing = conn.execute(
            "SELECT id FROM account WHERE email = ?", (email,)
        ).fetchone()
        if existing:
            raise ValueError("email already registered")
        account_id = uuid.uuid4().hex
        now = datetime.utcnow().isoformat()
        conn.execute(
            "INSERT INTO account (id, email, created_at) VALUES (?, ?, ?)",
            (account_id, email, now),
        )
        expires_at = (datetime.utcnow() + timedelta(days=30)).isoformat()
        conn.execute(
            "INSERT INTO subscription (account_id, tier, expires_at) VALUES (?, ?, ?)",
            (account_id, DEFAULT_TIER, expires_at),
        )
        conn.commit()
        return account_id
    finally:
        conn.close()


def get_account_by_email(db_path, email):
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT id, email FROM account WHERE email = ?", (email,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()