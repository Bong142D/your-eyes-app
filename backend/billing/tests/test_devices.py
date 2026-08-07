TEST_SERIALS = ["YE-TEST-0001", "YE-TEST-0002", "YE-TEST-0003", "YE-TEST-0004", "YE-TEST-0005"]


def _register_and_get_token(client, phone):
    reg = client.post("/accounts/register", json={"phone": phone})
    otp = reg.get_json()["otp"]
    verify = client.post(
        "/accounts/verify-otp",
        json={"phone": phone, "code": otp, "purpose": "register"},
    )
    data = verify.get_json()
    return data["account_id"], data["token"]


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def test_link_device_returns_device_id(client):
    _, token = _register_and_get_token(client, "0977777701")
    resp = client.post(
        "/devices/link",
        json={"serial_number": TEST_SERIALS[0]},
        headers=_auth_header(token),
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["device_id"]
    assert data["serial_number"] == TEST_SERIALS[0]
    assert data["status"] == "active"


def test_link_device_without_token_returns_401(client):
    resp = client.post("/devices/link", json={"serial_number": TEST_SERIALS[0]})
    assert resp.status_code == 401


def test_link_device_unknown_serial_returns_404(client):
    _, token = _register_and_get_token(client, "0977777702")
    resp = client.post(
        "/devices/link",
        json={"serial_number": "NOT-IN-CATALOG"},
        headers=_auth_header(token),
    )
    assert resp.status_code == 404


def test_link_device_already_linked_returns_409(client):
    _, token_a = _register_and_get_token(client, "0977777703")
    client.post(
        "/devices/link", json={"serial_number": TEST_SERIALS[1]}, headers=_auth_header(token_a)
    )
    _, token_b = _register_and_get_token(client, "0977777704")
    resp = client.post(
        "/devices/link", json={"serial_number": TEST_SERIALS[1]}, headers=_auth_header(token_b)
    )
    assert resp.status_code == 409


def test_get_device_info_requires_ownership(client):
    _, token_a = _register_and_get_token(client, "0977777705")
    link = client.post(
        "/devices/link", json={"serial_number": TEST_SERIALS[2]}, headers=_auth_header(token_a)
    )
    device_id = link.get_json()["device_id"]

    _, token_b = _register_and_get_token(client, "0977777706")
    resp = client.get(f"/devices/{device_id}", headers=_auth_header(token_b))
    assert resp.status_code == 403

    resp_ok = client.get(f"/devices/{device_id}", headers=_auth_header(token_a))
    assert resp_ok.status_code == 200
    assert resp_ok.get_json()["serial_number"] == TEST_SERIALS[2]


def test_list_devices_without_token_returns_401(client):
    resp = client.get("/devices")
    assert resp.status_code == 401


def test_list_devices_returns_empty_array_when_none_linked(client):
    _, token = _register_and_get_token(client, "0977777707")
    resp = client.get("/devices", headers=_auth_header(token))
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_list_devices_returns_only_own_devices(client):
    _, token_a = _register_and_get_token(client, "0977777708")
    client.post(
        "/devices/link", json={"serial_number": TEST_SERIALS[3]}, headers=_auth_header(token_a)
    )
    client.post(
        "/devices/link", json={"serial_number": TEST_SERIALS[4]}, headers=_auth_header(token_a)
    )

    _, token_b = _register_and_get_token(client, "0977777709")
    resp_b = client.get("/devices", headers=_auth_header(token_b))
    assert resp_b.status_code == 200
    assert resp_b.get_json() == []

    resp_a = client.get("/devices", headers=_auth_header(token_a))
    assert resp_a.status_code == 200
    serials = {device["serial_number"] for device in resp_a.get_json()}
    assert serials == {TEST_SERIALS[3], TEST_SERIALS[4]}
