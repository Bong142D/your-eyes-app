def test_consume_decrements_quota_remaining(client):
    reg = client.post("/accounts/register", json={"email": "e@example.com"})
    account_id = reg.get_json()["account_id"]
    dev = client.post(f"/accounts/{account_id}/devices")
    device_id = dev.get_json()["device_id"]

    resp = client.post(f"/devices/{device_id}/consume")
    assert resp.status_code == 200
    assert resp.get_json()["quota_remaining"] == 19

    status = client.get(f"/devices/{device_id}/status")
    assert status.get_json()["quota_remaining"] == 19


def test_consume_unknown_device_returns_404(client):
    resp = client.post("/devices/does-not-exist/consume")
    assert resp.status_code == 404