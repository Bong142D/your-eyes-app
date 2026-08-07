TEST_SERIALS = ["YE-TEST-0001", "YE-TEST-0002", "YE-TEST-0003", "YE-TEST-0004", "YE-TEST-0005"]


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def _setup_linked_device(client, phone, serial):
    reg = client.post("/accounts/register", json={"phone": phone})
    otp = reg.get_json()["otp"]
    verify = client.post(
        "/accounts/verify-otp", json={"phone": phone, "code": otp, "purpose": "register"}
    )
    verify_data = verify.get_json()
    token = verify_data["token"]
    link = client.post(
        "/devices/link", json={"serial_number": serial}, headers=_auth_header(token)
    )
    return link.get_json()["device_id"], token


def _get_action_otp(client, device_id, token):
    resp = client.post(f"/devices/{device_id}/request-action-otp", headers=_auth_header(token))
    return resp.get_json()["otp"]


def test_lock_requires_action_otp(client):
    device_id, token = _setup_linked_device(client, "0966000001", TEST_SERIALS[0])
    resp = client.post(f"/devices/{device_id}/lock", headers=_auth_header(token))
    assert resp.status_code == 400  # thiếu otp_code


def test_lock_with_wrong_otp_returns_401(client):
    device_id, token = _setup_linked_device(client, "0966000002", TEST_SERIALS[1])
    _get_action_otp(client, device_id, token)
    resp = client.post(
        f"/devices/{device_id}/lock", json={"otp_code": "000000"}, headers=_auth_header(token)
    )
    assert resp.status_code == 401


def test_lock_then_consume_is_blocked(client):
    device_id, token = _setup_linked_device(client, "0966000003", TEST_SERIALS[2])
    otp = _get_action_otp(client, device_id, token)
    lock_resp = client.post(
        f"/devices/{device_id}/lock", json={"otp_code": otp}, headers=_auth_header(token)
    )
    assert lock_resp.status_code == 200
    assert lock_resp.get_json()["status"] == "locked"

    consume_resp = client.post(f"/devices/{device_id}/consume")
    assert consume_resp.status_code == 403


def test_unlock_after_lock_restores_active(client):
    device_id, token = _setup_linked_device(client, "0966000004", TEST_SERIALS[3])
    otp = _get_action_otp(client, device_id, token)
    client.post(f"/devices/{device_id}/lock", json={"otp_code": otp}, headers=_auth_header(token))

    unlock_resp = client.post(f"/devices/{device_id}/unlock", headers=_auth_header(token))
    assert unlock_resp.status_code == 200
    assert unlock_resp.get_json()["status"] == "active"

    consume_resp = client.post(f"/devices/{device_id}/consume")
    assert consume_resp.status_code == 200


def test_unlock_when_not_locked_returns_409(client):
    device_id, token = _setup_linked_device(client, "0966000005", TEST_SERIALS[4])
    resp = client.post(f"/devices/{device_id}/unlock", headers=_auth_header(token))
    assert resp.status_code == 409


def test_report_lost_then_recover(client):
    device_id, token = _setup_linked_device(client, "0966000006", "YE-TEST-0001")
    otp = _get_action_otp(client, device_id, token)
    lost_resp = client.post(
        f"/devices/{device_id}/report-lost", json={"otp_code": otp}, headers=_auth_header(token)
    )
    assert lost_resp.status_code == 200
    assert lost_resp.get_json()["status"] == "lost"

    consume_resp = client.post(f"/devices/{device_id}/consume")
    assert consume_resp.status_code == 403

    recover_resp = client.post(f"/devices/{device_id}/recover", headers=_auth_header(token))
    assert recover_resp.status_code == 200
    assert recover_resp.get_json()["status"] == "active"


def test_reset_does_not_change_status_or_serial(client):
    device_id, token = _setup_linked_device(client, "0966000007", "YE-TEST-0002")
    resp = client.post(f"/devices/{device_id}/reset", headers=_auth_header(token))
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "active"

    info = client.get(f"/devices/{device_id}", headers=_auth_header(token)).get_json()
    assert info["serial_number"] == "YE-TEST-0002"
    assert info["last_reset_at"] is not None


def test_replace_device_closes_old_and_creates_new(client):
    device_id, token = _setup_linked_device(client, "0966000008", "YE-TEST-0003")
    otp = _get_action_otp(client, device_id, token)
    resp = client.post(
        f"/devices/{device_id}/replace",
        json={"new_serial_number": "YE-TEST-0004", "otp_code": otp},
        headers=_auth_header(token),
    )
    assert resp.status_code == 201
    new_device_id = resp.get_json()["device_id"]
    assert new_device_id != device_id

    old_info = client.get(f"/devices/{device_id}", headers=_auth_header(token)).get_json()
    assert old_info["status"] == "replaced"

    new_info = client.get(f"/devices/{new_device_id}", headers=_auth_header(token)).get_json()
    assert new_info["status"] == "active"
    assert new_info["serial_number"] == "YE-TEST-0004"

    # Kính cũ đã replaced thì không thể pairing lại serial cũ
    relink_resp = client.post(
        "/devices/link", json={"serial_number": "YE-TEST-0003"}, headers=_auth_header(token)
    )
    assert relink_resp.status_code == 409


def test_device_seen_updates_last_seen_and_battery(client):
    device_id, token = _setup_linked_device(client, "0966000009", "YE-TEST-0005")
    resp = client.post(
        f"/devices/{device_id}/seen",
        json={"channel": "bluetooth", "battery": 77, "firmware": "v2.2.0"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["message"]

    info = client.get(f"/devices/{device_id}", headers=_auth_header(token)).get_json()
    assert info["battery"] == 77
    assert info["firmware"] == "v2.2.0"
    assert info["last_seen_bluetooth_at"] is not None
    assert info["last_seen_cellular_at"] is None


def test_device_seen_invalid_channel_returns_400(client):
    device_id, _ = _setup_linked_device(client, "0966000010", "YE-TEST-0001")
    resp = client.post(f"/devices/{device_id}/seen", json={"channel": "wifi"})
    assert resp.status_code == 400
