def test_status_for_new_device_is_free_tier_and_valid(client):
    reg = client.post("/accounts/register", json={"email": "d@example.com"})
    account_id = reg.get_json()["account_id"]
    dev = client.post(f"/accounts/{account_id}/devices")
    device_id = dev.get_json()["device_id"]

    resp = client.get(f"/devices/{device_id}/status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["tier"] == "free"
    assert data["subscription_valid"] is True
    assert data["quota_remaining"] == 20
    assert data["allowed_intents"] == ["DOC_CHU"]


def test_status_unknown_device_returns_404(client):
    resp = client.get("/devices/does-not-exist/status")
    assert resp.status_code == 404