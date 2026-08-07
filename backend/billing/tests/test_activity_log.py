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


def test_add_activity_log_entry(client):
    device_id, token = _setup_linked_device(client, "0944400101", "YE-TEST-0001")
    resp = client.post(f"/devices/{device_id}/activity-log", json={"title": "Bắt đầu đi dạo"})
    assert resp.status_code == 200
    assert resp.get_json()["message"]

    log = client.get("/activity-log", headers=_auth_header(token)).get_json()
    assert len(log) == 1
    assert log[0]["title"] == "Bắt đầu đi dạo"


def test_activity_log_missing_title_returns_400(client):
    device_id, _ = _setup_linked_device(client, "0944400102", "YE-TEST-0002")
    resp = client.post(f"/devices/{device_id}/activity-log", json={})
    assert resp.status_code == 400


def test_activity_log_unknown_device_returns_404(client):
    resp = client.post("/devices/does-not-exist/activity-log", json={"title": "x"})
    assert resp.status_code == 404


def test_activity_log_without_token_returns_401(client):
    resp = client.get("/activity-log")
    assert resp.status_code == 401


def test_activity_log_returns_newest_first(client):
    device_id, token = _setup_linked_device(client, "0944400103", "YE-TEST-0003")
    client.post(f"/devices/{device_id}/activity-log", json={"title": "Bắt đầu đi dạo"})
    client.post(f"/devices/{device_id}/activity-log", json={"title": "Đã tới Công viên"})

    log = client.get("/activity-log", headers=_auth_header(token)).get_json()
    assert log[0]["title"] == "Đã tới Công viên"
    assert log[1]["title"] == "Bắt đầu đi dạo"
