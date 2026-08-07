def test_status_for_new_device_is_free_tier_and_valid(client):
    reg = client.post("/accounts/register", json={"phone": "0988888801"})
    otp = reg.get_json()["otp"]
    verify = client.post(
        "/accounts/verify-otp",
        json={"phone": "0988888801", "code": otp, "purpose": "register"},
    )
    verify_data = verify.get_json()
    token = verify_data["token"]
    dev = client.post(
        "/devices/link",
        json={"serial_number": "YE-TEST-0001"},
        headers={"Authorization": f"Bearer {token}"},
    )
    device_id = dev.get_json()["device_id"]

    resp = client.get(f"/devices/{device_id}/status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["tier"] == "free"
    assert data["subscription_valid"] is True
    assert data["quota_remaining"] == 20
    assert data["allowed_intents"] == ["DOC_CHU"]
    assert data["device_status"] == "active"


def test_status_unknown_device_returns_404(client):
    resp = client.get("/devices/does-not-exist/status")
    assert resp.status_code == 404