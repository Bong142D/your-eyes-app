CREATE TABLE IF NOT EXISTS account (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS device (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    paired_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS subscription (
    account_id TEXT PRIMARY KEY,
    tier TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS quota (
    account_id TEXT NOT NULL,
    period TEXT NOT NULL,
    used INTEGER NOT NULL DEFAULT 0,
    limit_value INTEGER NOT NULL,
    PRIMARY KEY (account_id, period)
);