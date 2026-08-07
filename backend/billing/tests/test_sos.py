def _setup_linked_device(client, phone, serial):
    reg = client.post("/accounts/register", json={"phone": phone})
    otp = reg.get_json()["otp"]
    verify = client.post(
        "/accounts/verify-otp", json={"phone": phone, "code": otp, "purpose": "register"}
    )
    verify_data = verify.get_json()
    token = verify_data["token"]
    link = client.post(
        "/devices/link", json={"serial_number": serial},
        headers={"Authorization": f"Bearer {token}"},
    )
    return link.get_json()["device_id"], token


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def test_sos_press_without_token_returns_401(client):
    device_id, _ = _setup_linked_device(client, "0922200001", "YE-TEST-0001")
    resp = client.post(f"/devices/{device_id}/sos/press")
    assert resp.status_code == 401


def test_sos_press_less_than_3_times_does_not_trigger(client):
    device_id, token = _setup_linked_device(client, "0922200002", "YE-TEST-0002")
    resp1 = client.post(f"/devices/{device_id}/sos/press", headers=_auth_header(token))
    assert resp1.get_json()["triggered"] is False
    assert resp1.get_json()["press_count"] == 1

    resp2 = client.post(f"/devices/{device_id}/sos/press", headers=_auth_header(token))
    assert resp2.get_json()["triggered"] is False
    assert resp2.get_json()["press_count"] == 2


def test_sos_press_3_times_triggers_and_notifies_all_contacts(client):
    device_id, token = _setup_linked_device(client, "0922200003", "YE-TEST-0003")
    client.post(
        "/emergency-contacts", json={"name": "Mẹ", "phone": "0911111111"},
        headers=_auth_header(token),
    )
    client.post(
        "/emergency-contacts", json={"name": "Anh", "phone": "0911222222"},
        headers=_auth_header(token),
    )

    client.post(f"/devices/{device_id}/sos/press", headers=_auth_header(token))
    client.post(f"/devices/{device_id}/sos/press", headers=_auth_header(token))
    resp3 = client.post(f"/devices/{device_id}/sos/press", headers=_auth_header(token))

    data = resp3.get_json()
    assert data["triggered"] is True
    assert data["sos_event_id"]
    assert data["location_token"]
    # 2 liên hệ x 2 kênh (sms + push) = 4 lượt gửi, tất cả "sent" (mock)
    assert len(data["deliveries"]) == 4
    assert all(d["status"] == "sent" for d in data["deliveries"])
    contact_names = {d["contact_name"] for d in data["deliveries"]}
    assert contact_names == {"Mẹ", "Anh"}


def test_sos_press_counter_resets_after_trigger(client):
    device_id, token = _setup_linked_device(client, "0922200004", "YE-TEST-0004")
    for _ in range(3):
        client.post(f"/devices/{device_id}/sos/press", headers=_auth_header(token))
    # Sau khi đã trigger, nhấn tiếp phải đếm lại từ 1, không kích hoạt lại ngay.
    resp = client.post(f"/devices/{device_id}/sos/press", headers=_auth_header(token))
    data = resp.get_json()
    assert data["triggered"] is False
    assert data["press_count"] == 1


def test_sos_creates_activity_log_entry(client):
    device_id, token = _setup_linked_device(client, "0922200005", "YE-TEST-0005")
    for _ in range(3):
        client.post(f"/devices/{device_id}/sos/press", headers=_auth_header(token))

    log = client.get("/activity-log", headers=_auth_header(token)).get_json()
    assert any(entry["title"] == "Đã gửi tín hiệu SOS" for entry in log)


def test_public_location_link_works_without_token(client):
    device_id, token = _setup_linked_device(client, "0922200006", "YE-TEST-0001")
    client.post(
        f"/devices/{device_id}/location", json={"lat": 10.7769, "lng": 106.7009}
    )
    result = None
    for _ in range(3):
        resp = client.post(f"/devices/{device_id}/sos/press", headers=_auth_header(token))
        result = resp.get_json()

    location_token = result["location_token"]
    public_resp = client.get(f"/sos/{location_token}")
    assert public_resp.status_code == 200
    data = public_resp.get_json()
    assert data["lat"] == 10.7769
    assert data["lng"] == 106.7009


def test_public_location_link_unknown_token_returns_404(client):
    resp = client.get("/sos/not-a-real-token")
    assert resp.status_code == 404


def test_sos_press_unknown_device_returns_401_without_token(client):
    resp = client.post("/devices/does-not-exist/sos/press")
    assert resp.status_code == 401
