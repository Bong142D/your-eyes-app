import app as billing_app


def _setup_linked_device_with_contacts(client, serial="YE-TEST-0001"):
    reg = client.post("/accounts/register", json={"phone": "0955500201"})
    otp = reg.get_json()["otp"]
    verify = client.post(
        "/accounts/verify-otp",
        json={"phone": "0955500201", "code": otp, "purpose": "register"},
    )
    token = verify.get_json()["token"]
    client.post(
        "/devices/link",
        json={"serial_number": serial},
        headers={"Authorization": f"Bearer {token}"},
    )

    client.post(
        "/emergency-contacts",
        json={"name": "Mẹ", "phone": "0911111111", "is_primary": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    client.post(
        "/emergency-contacts",
        json={"name": "Anh", "phone": "0911222222"},
        headers={"Authorization": f"Bearer {token}"},
    )
    return serial, token


def _internal_headers():
    return {"Authorization": f"Bearer {billing_app.INTERNAL_API_KEY}"}


def test_trigger_without_internal_key_returns_401(client, monkeypatch):
    # Setup (register/link/contacts) cần BILLING_ENV=dev để lấy OTP demo — chỉ chuyển sang
    # production ngay trước lời gọi cần test, vì middleware S2S bỏ qua kiểm tra khi dev
    # (quyết định 2026-08-01, demo Server Kính).
    serial, _ = _setup_linked_device_with_contacts(client)
    monkeypatch.setenv("BILLING_ENV", "production")
    resp = client.post(
        "/internal/api/v1/sos/trigger",
        json={"device_id": serial, "location": {"latitude": 10.0, "longitude": 106.0}},
    )
    assert resp.status_code == 401


def test_trigger_with_wrong_internal_key_returns_401(client, monkeypatch):
    serial, _ = _setup_linked_device_with_contacts(client)
    monkeypatch.setenv("BILLING_ENV", "production")
    resp = client.post(
        "/internal/api/v1/sos/trigger",
        json={"device_id": serial, "location": {"latitude": 10.0, "longitude": 106.0}},
        headers={"Authorization": "Bearer wrong-key"},
    )
    assert resp.status_code == 401


def test_trigger_with_user_session_token_is_rejected(client, monkeypatch):
    """Bearer token của người dùng KHÔNG được coi là hợp lệ cho route /internal/api/* —
    2 không gian giá trị khác nhau dù chung tên header (xem middleware trong app.py)."""
    serial, token = _setup_linked_device_with_contacts(client)
    monkeypatch.setenv("BILLING_ENV", "production")
    resp = client.post(
        "/internal/api/v1/sos/trigger",
        json={"device_id": serial, "location": {"latitude": 10.0, "longitude": 106.0}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401


def test_trigger_without_internal_key_succeeds_in_dev_env(client):
    """Ngược lại 3 test trên: ở BILLING_ENV=dev (mặc định test), middleware S2S bỏ qua kiểm
    tra key hoàn toàn — Server Kính gọi thẳng không cần header trong giai đoạn demo."""
    serial, _ = _setup_linked_device_with_contacts(client)
    resp = client.post(
        "/internal/api/v1/sos/trigger",
        json={"device_id": serial, "location": {"latitude": 10.0, "longitude": 106.0}},
    )
    assert resp.status_code == 202


def test_trigger_missing_fields_returns_400(client):
    serial, _ = _setup_linked_device_with_contacts(client)
    resp = client.post(
        "/internal/api/v1/sos/trigger",
        json={"device_id": serial},
        headers=_internal_headers(),
    )
    assert resp.status_code == 400


def test_trigger_unknown_device_returns_404(client):
    resp = client.post(
        "/internal/api/v1/sos/trigger",
        json={
            "device_id": "does-not-exist",
            "location": {"latitude": 10.0, "longitude": 106.0},
        },
        headers=_internal_headers(),
    )
    assert resp.status_code == 404


def test_trigger_returns_202_and_creates_sos_event(client):
    serial, token = _setup_linked_device_with_contacts(client)
    resp = client.post(
        "/internal/api/v1/sos/trigger",
        json={
            "device_id": serial,
            "location": {"latitude": 10.776889, "longitude": 106.700833},
            "timestamp_utc": "2026-08-01T10:00:00Z",
        },
        headers=_internal_headers(),
    )
    assert resp.status_code == 202
    assert resp.get_json()["status"] == "accepted"

    # Vị trí xem qua link công khai phải khớp toạ độ gửi lên (không cần location_log trước đó)
    log = client.get("/activity-log", headers={"Authorization": f"Bearer {token}"}).get_json()
    assert any(entry["title"] == "Đã gửi tín hiệu SOS" for entry in log)


def test_trigger_sends_sms_push_to_all_and_robocall_only_to_primary(client, db_path):
    import models

    serial, _ = _setup_linked_device_with_contacts(client, serial="YE-TEST-0003")
    result = models.trigger_sos_from_device(db_path, serial, 10.776889, 106.700833)

    assert result["primary_contact_notified"] is True
    channels_by_contact = {}
    for delivery in result["deliveries"]:
        channels_by_contact.setdefault(delivery["contact_name"], set()).add(delivery["channel"])

    assert channels_by_contact["Mẹ"] == {"sms", "push", "robocall"}  # Mẹ là primary
    assert channels_by_contact["Anh"] == {"sms", "push"}  # Anh không phải primary, không robo-call


def test_trigger_without_primary_contact_skips_robocall(client, db_path):
    import models

    reg = client.post("/accounts/register", json={"phone": "0955500202"})
    otp = reg.get_json()["otp"]
    verify = client.post(
        "/accounts/verify-otp",
        json={"phone": "0955500202", "code": otp, "purpose": "register"},
    )
    token = verify.get_json()["token"]
    client.post(
        "/devices/link", json={"serial_number": "YE-TEST-0002"},
        headers={"Authorization": f"Bearer {token}"},
    )
    client.post(
        "/emergency-contacts", json={"name": "Anh", "phone": "0911222222"},
        headers={"Authorization": f"Bearer {token}"},
    )

    result = models.trigger_sos_from_device(db_path, "YE-TEST-0002", 10.0, 106.0)
    assert result["primary_contact_notified"] is False
    assert all(d["channel"] != "robocall" for d in result["deliveries"])


# ---------------------------------------------------------------------------
# SOS tự dispatch 1 kinh_action_request cho CHÍNH thiết bị (mới 2026-08-02) — để app tự poll
# GET /devices/{id}/pending-actions và hiện màn hình cảnh báo toàn màn hình + xác nhận gọi
# liên hệ chính, thay cho kênh push (Expo Go không nhận push thật).
# ---------------------------------------------------------------------------

def test_trigger_with_primary_contact_creates_pending_action_for_own_device(client, db_path):
    serial, token = _setup_linked_device_with_contacts(client, serial="YE-TEST-0003")
    resp = client.post(
        "/internal/api/v1/sos/trigger",
        json={
            "device_id": serial,
            "location": {"latitude": 10.776889, "longitude": 106.700833},
            "timestamp_utc": "2026-08-01T10:00:00Z",
        },
        headers=_internal_headers(),
    )
    assert resp.status_code == 202

    link = client.get("/devices", headers={"Authorization": f"Bearer {token}"}).get_json()
    device_id = link[0]["id"]

    pending = client.get(
        f"/devices/{device_id}/pending-actions", headers={"Authorization": f"Bearer {token}"}
    ).get_json()
    assert len(pending) == 1
    assert pending[0]["action"] == "call_emergency_contact"
    assert pending[0]["params"]["sos"] is True
    assert pending[0]["params"]["contact_name"] == "Mẹ"
    assert pending[0]["params"]["contact_phone"] == "0911111111"


def test_trigger_without_primary_contact_does_not_create_pending_action(client, db_path):
    import models

    reg = client.post("/accounts/register", json={"phone": "0955500203"})
    otp = reg.get_json()["otp"]
    verify = client.post(
        "/accounts/verify-otp",
        json={"phone": "0955500203", "code": otp, "purpose": "register"},
    )
    token = verify.get_json()["token"]
    client.post(
        "/devices/link", json={"serial_number": "YE-TEST-0004"},
        headers={"Authorization": f"Bearer {token}"},
    )
    client.post(
        "/emergency-contacts", json={"name": "Anh", "phone": "0911222222"},
        headers={"Authorization": f"Bearer {token}"},
    )

    models.trigger_sos_from_device(db_path, "YE-TEST-0004", 10.0, 106.0)

    link = client.get("/devices", headers={"Authorization": f"Bearer {token}"}).get_json()
    device_id = link[0]["id"]
    pending = client.get(
        f"/devices/{device_id}/pending-actions", headers={"Authorization": f"Bearer {token}"}
    ).get_json()
    assert pending == []
