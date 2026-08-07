CREATE TABLE IF NOT EXISTS account (
    id TEXT PRIMARY KEY,
    phone TEXT UNIQUE NOT NULL,
    created_at TEXT NOT NULL,
    is_admin INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS device_catalog (
    serial_number TEXT PRIMARY KEY,
    provisioned_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS device (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    serial_number TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    battery INTEGER,
    firmware TEXT,
    last_seen_bluetooth_at TEXT,
    last_seen_cellular_at TEXT,
    last_reset_at TEXT,
    paired_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS subscription (
    account_id TEXT PRIMARY KEY,
    tier TEXT NOT NULL,
    billing_cycle TEXT NOT NULL DEFAULT 'monthly',
    expires_at TEXT NOT NULL,
    expiry_notified_at TEXT
);

CREATE TABLE IF NOT EXISTS quota (
    account_id TEXT NOT NULL,
    period TEXT NOT NULL,
    used INTEGER NOT NULL DEFAULT 0,
    limit_value INTEGER NOT NULL,
    PRIMARY KEY (account_id, period)
);

CREATE TABLE IF NOT EXISTS otp_request (
    phone TEXT NOT NULL,
    purpose TEXT NOT NULL,
    code TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    consumed_at TEXT,
    PRIMARY KEY (phone, purpose)
);

CREATE TABLE IF NOT EXISTS session (
    token TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked_at TEXT
);

CREATE TABLE IF NOT EXISTS discount_code (
    code TEXT PRIMARY KEY,
    percent_off INTEGER NOT NULL,
    expires_at TEXT,
    max_uses INTEGER,
    used_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS payment_transaction (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    tier TEXT NOT NULL,
    billing_cycle TEXT NOT NULL,
    amount INTEGER NOT NULL,
    discount_code TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    gateway_ref TEXT UNIQUE NOT NULL,
    created_at TEXT NOT NULL,
    paid_at TEXT
);

CREATE TABLE IF NOT EXISTS emergency_contact (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    is_primary INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS saved_place (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    place_type TEXT NOT NULL,
    label TEXT,
    lat REAL NOT NULL,
    lng REAL NOT NULL,
    address TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sos_press (
    device_id TEXT NOT NULL,
    pressed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sos_event (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    device_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'triggered',
    lat REAL,
    lng REAL,
    location_token TEXT UNIQUE,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sos_delivery (
    id TEXT PRIMARY KEY,
    sos_event_id TEXT NOT NULL,
    contact_phone TEXT NOT NULL,
    channel TEXT NOT NULL,
    status TEXT NOT NULL,
    sent_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS location_log (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    lat REAL NOT NULL,
    lng REAL NOT NULL,
    recorded_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS activity_log_entry (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    title TEXT NOT NULL,
    recorded_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outbound_notification (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    device_id TEXT NOT NULL,
    payload TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    created_at TEXT NOT NULL,
    sent_at TEXT
);

CREATE TABLE IF NOT EXISTS community_group (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS group_membership (
    account_id TEXT NOT NULL,
    group_id TEXT NOT NULL,
    joined_at TEXT NOT NULL,
    PRIMARY KEY (account_id, group_id)
);

CREATE TABLE IF NOT EXISTS community_post (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    author_name TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS community_event (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    event_time TEXT NOT NULL,
    location TEXT
);

CREATE TABLE IF NOT EXISTS saved_event (
    account_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    saved_at TEXT NOT NULL,
    PRIMARY KEY (account_id, event_id)
);

CREATE TABLE IF NOT EXISTS support_article (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS support_ticket (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL,
    resolved_at TEXT
);

CREATE TABLE IF NOT EXISTS hotline_call_log (
    id TEXT PRIMARY KEY,
    account_id TEXT,
    called_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS device_push_token (
    device_id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    push_token TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS kinh_action_request (
    request_id TEXT PRIMARY KEY,
    device_id TEXT NOT NULL,
    action TEXT NOT NULL,
    params TEXT NOT NULL,
    dispatch_status TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS kinh_action_report (
    id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL,
    status TEXT NOT NULL,
    detail TEXT,
    reported_at TEXT NOT NULL
);