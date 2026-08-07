def test_consume_decrements_quota_remaining(client):
    reg = client.post("/accounts/register", json={"phone": "0999999901"})
    otp = reg.get_json()["otp"]
    verify = client.post(
        "/accounts/verify-otp",
        json={"phone": "0999999901", "code": otp, "purpose": "register"},
    )
    verify_data = verify.get_json()
    token = verify_data["token"]
    dev = client.post(
        "/devices/link",
        json={"serial_number": "YE-TEST-0002"},
        headers={"Authorization": f"Bearer {token}"},
    )
    device_id = dev.get_json()["device_id"]

    resp = client.post(f"/devices/{device_id}/consume")
    assert resp.status_code == 200
    assert resp.get_json()["quota_remaining"] == 19

    status = client.get(f"/devices/{device_id}/status")
    assert status.get_json()["quota_remaining"] == 19


def test_consume_unknown_device_returns_404(client):
    resp = client.post("/devices/does-not-exist/consume")
    assert resp.status_code == 404