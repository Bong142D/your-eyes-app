def test_pair_device_returns_device_id(client):
    reg = client.post("/accounts/register", json={"email": "c@example.com"})
    account_id = reg.get_json()["account_id"]
    resp = client.post(f"/accounts/{account_id}/devices")
    assert resp.status_code == 201
    assert resp.get_json()["device_id"]


def test_pair_device_unknown_account_returns_404(client):
    resp = client.post("/accounts/does-not-exist/devices")
    assert resp.status_code == 404