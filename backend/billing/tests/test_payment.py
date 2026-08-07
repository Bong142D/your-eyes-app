import models


def _register_and_get_token(client, phone):
    reg = client.post("/accounts/register", json={"phone": phone})
    otp = reg.get_json()["otp"]
    verify = client.post(
        "/accounts/verify-otp", json={"phone": phone, "code": otp, "purpose": "register"}
    )
    data = verify.get_json()
    return data["account_id"], data["token"]


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def test_list_packages_returns_pricing(client):
    resp = client.get("/packages")
    assert resp.status_code == 200
    data = resp.get_json()
    tiers = {p["tier"]: p for p in data}
    assert tiers["free"]["monthly_price"] == 0
    assert tiers["basic"]["monthly_price"] == 99000
    assert tiers["pro"]["yearly_price"] == 199000 * 12


def test_checkout_without_token_returns_401(client):
    resp = client.post("/payment/checkout", json={"tier": "basic", "billing_cycle": "monthly"})
    assert resp.status_code == 401


def test_checkout_invalid_tier_returns_400(client):
    _, token = _register_and_get_token(client, "0955500001")
    resp = client.post(
        "/payment/checkout",
        json={"tier": "enterprise", "billing_cycle": "monthly"},
        headers=_auth_header(token),
    )
    assert resp.status_code == 400


def test_checkout_returns_pending_transaction(client):
    _, token = _register_and_get_token(client, "0955500002")
    resp = client.post(
        "/payment/checkout",
        json={"tier": "basic", "billing_cycle": "monthly"},
        headers=_auth_header(token),
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["amount"] == 99000
    assert data["transaction_id"]
    assert data["gateway_ref"]


def test_checkout_yearly_is_twelve_times_monthly(client):
    _, token = _register_and_get_token(client, "0955500003")
    resp = client.post(
        "/payment/checkout",
        json={"tier": "pro", "billing_cycle": "yearly"},
        headers=_auth_header(token),
    )
    assert resp.get_json()["amount"] == 199000 * 12


def test_checkout_with_discount_code_applies_percent_off(client, db_path):
    models.add_discount_code(db_path, "SALE20", percent_off=20)
    _, token = _register_and_get_token(client, "0955500004")
    resp = client.post(
        "/payment/checkout",
        json={"tier": "basic", "billing_cycle": "monthly", "discount_code": "SALE20"},
        headers=_auth_header(token),
    )
    assert resp.status_code == 201
    assert resp.get_json()["amount"] == 79200  # 99000 * 0.8


def test_checkout_with_invalid_discount_code_returns_400(client):
    _, token = _register_and_get_token(client, "0955500005")
    resp = client.post(
        "/payment/checkout",
        json={"tier": "basic", "billing_cycle": "monthly", "discount_code": "NOPE"},
        headers=_auth_header(token),
    )
    assert resp.status_code == 400


def test_webhook_paid_activates_subscription(client):
    account_id, token = _register_and_get_token(client, "0955500006")
    checkout = client.post(
        "/payment/checkout",
        json={"tier": "pro", "billing_cycle": "monthly"},
        headers=_auth_header(token),
    ).get_json()

    webhook_resp = client.post(
        "/payment/webhook", json={"gateway_ref": checkout["gateway_ref"], "status": "paid"}
    )
    assert webhook_resp.status_code == 200
    assert webhook_resp.get_json()["status"] == "paid"

    sub_resp = client.get("/subscription", headers=_auth_header(token))
    sub_data = sub_resp.get_json()
    assert sub_data["tier"] == "pro"
    assert sub_data["status"] == "active"


def test_webhook_failed_does_not_activate_subscription(client):
    _, token = _register_and_get_token(client, "0955500007")
    checkout = client.post(
        "/payment/checkout",
        json={"tier": "pro", "billing_cycle": "monthly"},
        headers=_auth_header(token),
    ).get_json()

    client.post(
        "/payment/webhook", json={"gateway_ref": checkout["gateway_ref"], "status": "failed"}
    )
    sub_resp = client.get("/subscription", headers=_auth_header(token))
    assert sub_resp.get_json()["tier"] == "free"


def test_webhook_is_idempotent(client):
    _, token = _register_and_get_token(client, "0955500008")
    checkout = client.post(
        "/payment/checkout",
        json={"tier": "basic", "billing_cycle": "monthly"},
        headers=_auth_header(token),
    ).get_json()

    first = client.post(
        "/payment/webhook", json={"gateway_ref": checkout["gateway_ref"], "status": "paid"}
    )
    assert first.get_json()["already_processed"] is False

    second = client.post(
        "/payment/webhook", json={"gateway_ref": checkout["gateway_ref"], "status": "paid"}
    )
    assert second.status_code == 200
    assert second.get_json()["already_processed"] is True


def test_webhook_unknown_gateway_ref_returns_404(client):
    resp = client.post(
        "/payment/webhook", json={"gateway_ref": "MOCKPAY-doesnotexist", "status": "paid"}
    )
    assert resp.status_code == 404


def test_paid_upgrade_unlocks_higher_quota(client):
    account_id, token = _register_and_get_token(client, "0955500009")
    link = client.post(
        "/devices/link",
        json={"serial_number": "YE-TEST-0001"},
        headers=_auth_header(token),
    )
    device_id = link.get_json()["device_id"]

    status_before = client.get(f"/devices/{device_id}/status").get_json()
    assert status_before["tier"] == "free"
    assert status_before["quota_remaining"] == 20

    checkout = client.post(
        "/payment/checkout",
        json={"tier": "pro", "billing_cycle": "monthly"},
        headers=_auth_header(token),
    ).get_json()
    client.post(
        "/payment/webhook", json={"gateway_ref": checkout["gateway_ref"], "status": "paid"}
    )

    status_after = client.get(f"/devices/{device_id}/status").get_json()
    assert status_after["tier"] == "pro"
    assert status_after["quota_remaining"] == 2000
