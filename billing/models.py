import sqlite3
import uuid
from datetime import datetime, timedelta

from tiers import DEFAULT_TIER, TIERS

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


def create_device(db_path, account_id):
    conn = _connect(db_path)
    try:
        account = conn.execute(
            "SELECT id FROM account WHERE id = ?", (account_id,)
        ).fetchone()
        if not account:
            return None
        device_id = uuid.uuid4().hex
        now = datetime.utcnow().isoformat()
        conn.execute(
            "INSERT INTO device (id, account_id, paired_at) VALUES (?, ?, ?)",
            (device_id, account_id, now),
        )
        conn.commit()
        return device_id
    finally:
        conn.close()


def _today_period():
    return datetime.utcnow().strftime("%Y-%m-%d")


def get_device_status(db_path, device_id):
    conn = _connect(db_path)
    try:
        device = conn.execute(
            "SELECT account_id FROM device WHERE id = ?", (device_id,)
        ).fetchone()
        if not device:
            return None
        account_id = device["account_id"]
        sub = conn.execute(
            "SELECT tier, expires_at FROM subscription WHERE account_id = ?",
            (account_id,),
        ).fetchone()
        tier = sub["tier"] if sub else DEFAULT_TIER
        now = datetime.utcnow().isoformat()
        subscription_valid = bool(sub) and sub["expires_at"] > now
        period = _today_period()
        quota_row = conn.execute(
            "SELECT used, limit_value FROM quota WHERE account_id = ? AND period = ?",
            (account_id, period),
        ).fetchone()
        tier_info = TIERS.get(tier, TIERS[DEFAULT_TIER])
        if quota_row:
            remaining = max(0, quota_row["limit_value"] - quota_row["used"])
        else:
            remaining = tier_info["quota_limit"]
        return {
            "tier": tier,
            "subscription_valid": subscription_valid,
            "quota_remaining": remaining,
            "allowed_intents": tier_info["allowed_intents"],
        }
    finally:
        conn.close()


def consume_quota(db_path, device_id):
    conn = _connect(db_path)
    try:
        device = conn.execute(
            "SELECT account_id FROM device WHERE id = ?", (device_id,)
        ).fetchone()
        if not device:
            return None
        account_id = device["account_id"]
        sub = conn.execute(
            "SELECT tier FROM subscription WHERE account_id = ?", (account_id,)
        ).fetchone()
        tier = sub["tier"] if sub else DEFAULT_TIER
        tier_limit = TIERS.get(tier, TIERS[DEFAULT_TIER])["quota_limit"]
        period = _today_period()
        row = conn.execute(
            "SELECT used, limit_value FROM quota WHERE account_id = ? AND period = ?",
            (account_id, period),
        ).fetchone()
        if row:
            used = row["used"] + 1
            limit_value = row["limit_value"]
            conn.execute(
                "UPDATE quota SET used = ? WHERE account_id = ? AND period = ?",
                (used, account_id, period),
            )
        else:
            used = 1
            limit_value = tier_limit
            conn.execute(
                "INSERT INTO quota (account_id, period, used, limit_value) VALUES (?, ?, ?, ?)",
                (account_id, period, used, limit_value),
            )
        conn.commit()
        return max(0, limit_value - used)
    finally:
        conn.close()
