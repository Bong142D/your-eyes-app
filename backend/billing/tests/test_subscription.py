from datetime import datetime, timedelta

import models


def _make_account_with_subscription(db_path, phone, tier, expires_in_days):
    account_id = models.create_account(db_path, phone)
    conn = models._connect(db_path)
    try:
        expires_at = (datetime.utcnow() + timedelta(days=expires_in_days)).isoformat()
        conn.execute(
            "UPDATE subscription SET tier = ?, expires_at = ? WHERE account_id = ?",
            (tier, expires_at, account_id),
        )
        conn.commit()
    finally:
        conn.close()
    return account_id


def test_subscription_far_from_expiry_is_active(tmp_path):
    db_path = str(tmp_path / "test.db")
    models.init_db(db_path)
    account_id = _make_account_with_subscription(db_path, "0944400001", "basic", 20)
    status = models.get_subscription_status(db_path, account_id)
    assert status["status"] == "active"
    assert status["tier"] == "basic"


def test_subscription_within_7_days_is_expiring_soon(tmp_path):
    db_path = str(tmp_path / "test.db")
    models.init_db(db_path)
    account_id = _make_account_with_subscription(db_path, "0944400002", "basic", 5)
    status = models.get_subscription_status(db_path, account_id)
    assert status["status"] == "expiring_soon"
    assert status["tier"] == "basic"  # vẫn dùng tier đã mua cho tới khi thực sự hết hạn


def test_subscription_past_expiry_is_expired_and_downgraded_to_free(tmp_path):
    db_path = str(tmp_path / "test.db")
    models.init_db(db_path)
    account_id = _make_account_with_subscription(db_path, "0944400003", "pro", -1)
    status = models.get_subscription_status(db_path, account_id)
    assert status["status"] == "expired"
    assert status["tier"] == "free"  # hạ ngay khi hết hạn (đã chốt)
    assert status["purchased_tier"] == "pro"  # vẫn giữ lại gói đã mua để hiển thị lịch sử


def test_expired_subscription_blocks_higher_quota_on_device(tmp_path):
    db_path = str(tmp_path / "test.db")
    models.init_db(db_path)
    account_id = _make_account_with_subscription(db_path, "0944400004", "pro", -1)
    models.add_catalog_serial(db_path, "YE-SUBTEST-0001")
    device_id = models.link_device(db_path, account_id, "YE-SUBTEST-0001")

    status = models.get_device_status(db_path, device_id)
    assert status["tier"] == "free"
    assert status["quota_remaining"] == 20
    assert status["subscription_valid"] is False


def test_get_subscription_status_unknown_account_returns_none(tmp_path):
    db_path = str(tmp_path / "test.db")
    models.init_db(db_path)
    assert models.get_subscription_status(db_path, "not-a-real-account") is None


# ---------------------------------------------------------------------------
# scan_and_notify_expired_subscriptions (chủ động, quyết định 2026-08-01)
# ---------------------------------------------------------------------------

def test_scan_detects_expired_and_marks_notified(tmp_path):
    db_path = str(tmp_path / "test.db")
    models.init_db(db_path)
    account_id = _make_account_with_subscription(db_path, "0944400010", "pro", -1)

    checked = models.scan_and_notify_expired_subscriptions(db_path)
    assert checked == 1

    conn = models._connect(db_path)
    try:
        row = conn.execute(
            "SELECT expiry_notified_at FROM subscription WHERE account_id = ?", (account_id,)
        ).fetchone()
    finally:
        conn.close()
    assert row["expiry_notified_at"] is not None


def test_scan_is_idempotent_second_call_returns_zero(tmp_path):
    db_path = str(tmp_path / "test.db")
    models.init_db(db_path)
    _make_account_with_subscription(db_path, "0944400011", "pro", -1)

    assert models.scan_and_notify_expired_subscriptions(db_path) == 1
    assert models.scan_and_notify_expired_subscriptions(db_path) == 0


def test_scan_ignores_active_and_already_notified_subscriptions(tmp_path):
    db_path = str(tmp_path / "test.db")
    models.init_db(db_path)
    _make_account_with_subscription(db_path, "0944400012", "basic", 10)  # còn hạn, bỏ qua
    already = _make_account_with_subscription(db_path, "0944400013", "pro", -1)
    models.get_subscription_status(db_path, already)  # đường lazy phát hiện trước, tự flag

    assert models.scan_and_notify_expired_subscriptions(db_path) == 0


def test_scan_notifies_glasses_server_for_linked_active_device(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    models.init_db(db_path)
    account_id = _make_account_with_subscription(db_path, "0944400014", "pro", -1)
    models.add_catalog_serial(db_path, "YE-SCAN-0001")
    models.link_device(db_path, account_id, "YE-SCAN-0001")

    calls = []
    monkeypatch.setattr(
        models.requests, "post",
        lambda url, json, headers, timeout: calls.append(json) or _FakeOkResponse(),
    )

    models.scan_and_notify_expired_subscriptions(db_path)

    assert len(calls) == 1
    assert calls[0]["device_id"] == "YE-SCAN-0001"
    assert calls[0]["subscription"]["status"] == "expired"
    assert calls[0]["subscription"]["plan_id"] == "pro_monthly"


def test_scan_pushes_to_app_when_push_token_registered(tmp_path, monkeypatch, caplog):
    import logging

    db_path = str(tmp_path / "test.db")
    models.init_db(db_path)
    account_id = _make_account_with_subscription(db_path, "0944400015", "pro", -1)
    models.add_catalog_serial(db_path, "YE-SCAN-0002")
    device_id = models.link_device(db_path, account_id, "YE-SCAN-0002")
    models.register_push_token(db_path, device_id, "android", "tok-scan-1")

    caplog.set_level(logging.INFO, logger="models")
    models.scan_and_notify_expired_subscriptions(db_path)

    assert any(
        "SIMULATING_PUSH_SUBSCRIPTION_EXPIRED" in r.message and device_id in r.message
        for r in caplog.records
    )


def test_scan_skips_push_when_no_push_token(tmp_path, caplog):
    import logging

    db_path = str(tmp_path / "test.db")
    models.init_db(db_path)
    account_id = _make_account_with_subscription(db_path, "0944400016", "pro", -1)
    models.add_catalog_serial(db_path, "YE-SCAN-0003")
    models.link_device(db_path, account_id, "YE-SCAN-0003")  # không đăng ký push token

    caplog.set_level(logging.INFO, logger="models")
    models.scan_and_notify_expired_subscriptions(db_path)

    assert not any("SIMULATING_PUSH_SUBSCRIPTION_EXPIRED" in r.message for r in caplog.records)


class _FakeOkResponse:
    status_code = 200
    text = ""


def test_check_expiry_endpoint_requires_admin(client):
    reg = client.post("/accounts/register", json={"phone": "0944400020"})
    otp = reg.get_json()["otp"]
    verify = client.post(
        "/accounts/verify-otp", json={"phone": "0944400020", "code": otp, "purpose": "register"}
    )
    token = verify.get_json()["token"]
    resp = client.post(
        "/admin/subscriptions/check-expiry", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 403


def test_check_expiry_endpoint_returns_count(client, db_path):
    reg = client.post("/accounts/register", json={"phone": "0944400021"})
    otp = reg.get_json()["otp"]
    verify = client.post(
        "/accounts/verify-otp", json={"phone": "0944400021", "code": otp, "purpose": "register"}
    )
    admin_id, token = verify.get_json()["account_id"], verify.get_json()["token"]
    models.set_is_admin(db_path, admin_id, True)

    conn = models._connect(db_path)
    try:
        expires_at = (datetime.utcnow() - timedelta(days=1)).isoformat()
        conn.execute(
            "UPDATE subscription SET tier = 'pro', expires_at = ? WHERE account_id = ?",
            (expires_at, admin_id),
        )
        conn.commit()
    finally:
        conn.close()

    resp = client.post(
        "/admin/subscriptions/check-expiry", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert resp.get_json() == {"checked": 1}
