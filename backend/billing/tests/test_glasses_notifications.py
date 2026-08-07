import models


class _FakeResponse:
    def __init__(self, status_code, text=""):
        self.status_code = status_code
        self.text = text


def _register_link_and_token(client, phone, serial):
    reg = client.post("/accounts/register", json={"phone": phone})
    otp = reg.get_json()["otp"]
    verify = client.post(
        "/accounts/verify-otp", json={"phone": phone, "code": otp, "purpose": "register"}
    )
    data = verify.get_json()
    account_id, token = data["account_id"], data["token"]
    client.post(
        "/devices/link", json={"serial_number": serial},
        headers={"Authorization": f"Bearer {token}"},
    )
    return account_id, token


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def test_notify_success_marks_sent(db_path, monkeypatch):
    # conftest.py đã mock models.requests.post mặc định trả 200 — dùng luôn cho bước setup
    # (link_device tự bắn 1 thông báo "linked") để không nhiễu vào phần đang test.
    models.init_db(db_path)
    account_id = models.create_account(db_path, "0977000001")
    models.add_catalog_serial(db_path, "YE-NOTIFY-0001")
    models.link_device(db_path, account_id, "YE-NOTIFY-0001")

    calls = []

    def fake_post(url, json, headers, timeout):
        calls.append((url, json, headers))
        return _FakeResponse(200)

    monkeypatch.setattr(models.requests, "post", fake_post)

    models.notify_glasses_subscription_status(
        db_path, "YE-NOTIFY-0001", plan_id="pro_monthly", status="active",
        expires_at="2027-01-01T00:00:00",
    )

    assert len(calls) == 1
    url, payload, headers = calls[0]
    assert url.endswith("/internal/api/v1/devices/subscription-status")
    assert payload["device_id"] == "YE-NOTIFY-0001"
    assert payload["subscription"] == {
        "plan_id": "pro_monthly", "status": "active", "expires_at": "2027-01-01 00:00:00",
    }
    assert headers["Authorization"] == f"Bearer {models.INTERNAL_API_KEY}"
    assert models.list_failed_notifications(db_path) == []


def test_notify_failure_is_logged_and_can_be_retried(db_path, monkeypatch):
    models.init_db(db_path)
    account_id = models.create_account(db_path, "0977000002")
    models.add_catalog_serial(db_path, "YE-NOTIFY-0002")
    models.link_device(db_path, account_id, "YE-NOTIFY-0002")  # dùng mock mặc định (sent)

    call_count = {"n": 0}

    def fake_post(url, json, headers, timeout):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise ConnectionError("Server Kính không phản hồi")
        return _FakeResponse(200)

    monkeypatch.setattr(models.requests, "post", fake_post)

    models.notify_glasses_subscription_status(
        db_path, "YE-NOTIFY-0002", plan_id="basic_monthly", status="active", expires_at=None
    )

    failed = models.list_failed_notifications(db_path)
    assert len(failed) == 1
    assert "Server Kính không phản hồi" in failed[0]["last_error"]

    retried = models.retry_failed_notifications(db_path)
    assert retried == 1
    assert models.list_failed_notifications(db_path) == []


def test_notify_http_error_status_is_treated_as_failure(db_path, monkeypatch):
    models.init_db(db_path)
    account_id = models.create_account(db_path, "0977000003")
    models.add_catalog_serial(db_path, "YE-NOTIFY-0003")
    models.link_device(db_path, account_id, "YE-NOTIFY-0003")  # dùng mock mặc định (sent)

    monkeypatch.setattr(
        models.requests, "post", lambda url, json, headers, timeout: _FakeResponse(500, "boom")
    )

    models.notify_glasses_subscription_status(
        db_path, "YE-NOTIFY-0003", plan_id="pro_yearly", status="active", expires_at=None
    )
    failed = models.list_failed_notifications(db_path)
    assert len(failed) == 1
    assert "500" in failed[0]["last_error"]


def test_payment_webhook_paid_notifies_glasses_server(client, db_path, monkeypatch):
    _, token = _register_link_and_token(client, "0977000004", "YE-TEST-0001")

    calls = []
    monkeypatch.setattr(
        models.requests, "post",
        lambda url, json, headers, timeout: calls.append(json) or _FakeResponse(200),
    )

    checkout = client.post(
        "/payment/checkout", json={"tier": "pro", "billing_cycle": "monthly"},
        headers=_auth_header(token),
    ).get_json()
    client.post(
        "/payment/webhook", json={"gateway_ref": checkout["gateway_ref"], "status": "paid"}
    )

    assert len(calls) == 1
    assert calls[0]["device_id"] == "YE-TEST-0001"
    assert calls[0]["subscription"]["plan_id"] == "pro_monthly"
    assert calls[0]["subscription"]["status"] == "active"


def test_payment_webhook_failed_does_not_notify_glasses_server(client, db_path, monkeypatch):
    _, token = _register_link_and_token(client, "0977000005", "YE-TEST-0002")

    calls = []
    monkeypatch.setattr(
        models.requests, "post",
        lambda url, json, headers, timeout: calls.append(json) or _FakeResponse(200),
    )

    checkout = client.post(
        "/payment/checkout", json={"tier": "pro", "billing_cycle": "monthly"},
        headers=_auth_header(token),
    ).get_json()
    client.post(
        "/payment/webhook", json={"gateway_ref": checkout["gateway_ref"], "status": "failed"}
    )
    assert calls == []


def test_refund_notifies_glasses_server_with_cancelled_status(client, db_path, monkeypatch):
    account_id, token = _register_link_and_token(client, "0977000006", "YE-TEST-0003")
    models.set_is_admin(db_path, account_id, True)
    checkout = client.post(
        "/payment/checkout", json={"tier": "pro", "billing_cycle": "monthly"},
        headers=_auth_header(token),
    ).get_json()
    client.post(
        "/payment/webhook", json={"gateway_ref": checkout["gateway_ref"], "status": "paid"}
    )

    calls = []
    monkeypatch.setattr(
        models.requests, "post",
        lambda url, json, headers, timeout: calls.append(json) or _FakeResponse(200),
    )

    client.post(
        f"/admin/transactions/{checkout['transaction_id']}/refund",
        headers=_auth_header(token),
    )
    assert len(calls) == 1
    assert calls[0]["device_id"] == "YE-TEST-0003"
    assert calls[0]["subscription"]["status"] == "cancelled"


def test_link_device_notifies_linked_and_replace_notifies_unlinked_then_linked(
    client, db_path, monkeypatch
):
    _register_link_and_token(client, "0977000009", "YE-TEST-0004")

    calls = []
    monkeypatch.setattr(
        models.requests, "post",
        lambda url, json, headers, timeout: calls.append(json) or _FakeResponse(200),
    )

    # replace_device nhận device.id nội bộ (không phải serial) — tra ngược từ serial để gọi.
    conn = models._connect(db_path)
    row = conn.execute("SELECT id FROM device WHERE serial_number = 'YE-TEST-0004'").fetchone()
    conn.close()
    models.replace_device(db_path, row["id"], "YE-TEST-0005")

    assert len(calls) == 2
    assert calls[0]["device_id"] == "YE-TEST-0004"
    assert calls[0]["link_status"]["status"] == "unlinked"
    assert calls[1]["device_id"] == "YE-TEST-0005"
    assert calls[1]["link_status"]["status"] == "linked"


def test_admin_failed_notifications_routes_require_admin(client):
    reg = client.post("/accounts/register", json={"phone": "0977000007"})
    otp = reg.get_json()["otp"]
    verify = client.post(
        "/accounts/verify-otp",
        json={"phone": "0977000007", "code": otp, "purpose": "register"},
    )
    token = verify.get_json()["token"]

    list_resp = client.get("/admin/notifications/failed", headers=_auth_header(token))
    assert list_resp.status_code == 403

    retry_resp = client.post("/admin/notifications/retry-failed", headers=_auth_header(token))
    assert retry_resp.status_code == 403


def test_admin_can_list_and_retry_failed_notifications(client, db_path, monkeypatch):
    reg = client.post("/accounts/register", json={"phone": "0977000008"})
    otp = reg.get_json()["otp"]
    verify = client.post(
        "/accounts/verify-otp",
        json={"phone": "0977000008", "code": otp, "purpose": "register"},
    )
    admin_id, token = verify.get_json()["account_id"], verify.get_json()["token"]
    models.set_is_admin(db_path, admin_id, True)
    models.link_device(db_path, admin_id, "YE-TEST-0004")  # dùng mock mặc định (sent)

    monkeypatch.setattr(
        models.requests, "post",
        lambda url, json, headers, timeout: (_ for _ in ()).throw(ConnectionError("down")),
    )
    models.notify_glasses_subscription_status(
        db_path, "YE-TEST-0004", plan_id="pro_monthly", status="active", expires_at=None
    )

    list_resp = client.get("/admin/notifications/failed", headers=_auth_header(token))
    assert list_resp.status_code == 200
    assert len(list_resp.get_json()) == 1

    monkeypatch.setattr(
        models.requests, "post", lambda url, json, headers, timeout: _FakeResponse(200)
    )
    retry_resp = client.post("/admin/notifications/retry-failed", headers=_auth_header(token))
    assert retry_resp.status_code == 200
    assert retry_resp.get_json()["retried"] == 1
    assert client.get("/admin/notifications/failed", headers=_auth_header(token)).get_json() == []
