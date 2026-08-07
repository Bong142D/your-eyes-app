from datetime import datetime, timedelta

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


def _make_admin(db_path, client, phone):
    account_id, token = _register_and_get_token(client, phone)
    models.set_is_admin(db_path, account_id, True)
    return account_id, token


def _paid_transaction(client, db_path, phone, tier="pro"):
    account_id, token = _register_and_get_token(client, phone)
    checkout = client.post(
        "/payment/checkout",
        json={"tier": tier, "billing_cycle": "monthly"},
        headers=_auth_header(token),
    ).get_json()
    client.post(
        "/payment/webhook", json={"gateway_ref": checkout["gateway_ref"], "status": "paid"}
    )
    return account_id, token, checkout["transaction_id"]


def _set_paid_at(db_path, transaction_id, paid_at):
    conn = models._connect(db_path)
    try:
        conn.execute(
            "UPDATE payment_transaction SET paid_at = ? WHERE id = ?",
            (paid_at.isoformat(), transaction_id),
        )
        conn.commit()
    finally:
        conn.close()


def test_refund_without_admin_returns_403(client, db_path):
    _, _, transaction_id = _paid_transaction(client, db_path, "0933300001")
    _, non_admin_token = _register_and_get_token(client, "0933300002")
    resp = client.post(
        f"/admin/transactions/{transaction_id}/refund", headers=_auth_header(non_admin_token)
    )
    assert resp.status_code == 403


def test_refund_without_token_returns_401(client, db_path):
    _, _, transaction_id = _paid_transaction(client, db_path, "0933300003")
    resp = client.post(f"/admin/transactions/{transaction_id}/refund")
    assert resp.status_code == 401


def test_refund_within_window_downgrades_to_free(client, db_path):
    _, admin_token = _make_admin(db_path, client, "0933300004")
    account_id, user_token, transaction_id = _paid_transaction(client, db_path, "0933300005")

    resp = client.post(
        f"/admin/transactions/{transaction_id}/refund", headers=_auth_header(admin_token)
    )
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "refunded"

    sub = client.get("/subscription", headers=_auth_header(user_token)).get_json()
    assert sub["tier"] == "free"


def test_refund_pending_transaction_returns_409(client, db_path):
    _, admin_token = _make_admin(db_path, client, "0933300006")
    _, user_token = _register_and_get_token(client, "0933300007")
    checkout = client.post(
        "/payment/checkout",
        json={"tier": "basic", "billing_cycle": "monthly"},
        headers=_auth_header(user_token),
    ).get_json()

    resp = client.post(
        f"/admin/transactions/{checkout['transaction_id']}/refund",
        headers=_auth_header(admin_token),
    )
    assert resp.status_code == 409


def test_refund_twice_returns_409(client, db_path):
    _, admin_token = _make_admin(db_path, client, "0933300008")
    _, _, transaction_id = _paid_transaction(client, db_path, "0933300009")

    first = client.post(
        f"/admin/transactions/{transaction_id}/refund", headers=_auth_header(admin_token)
    )
    assert first.status_code == 200
    second = client.post(
        f"/admin/transactions/{transaction_id}/refund", headers=_auth_header(admin_token)
    )
    assert second.status_code == 409


def test_refund_outside_window_returns_409(client, db_path):
    _, admin_token = _make_admin(db_path, client, "0933300010")
    _, _, transaction_id = _paid_transaction(client, db_path, "0933300011")
    _set_paid_at(db_path, transaction_id, datetime.utcnow() - timedelta(days=8))

    resp = client.post(
        f"/admin/transactions/{transaction_id}/refund", headers=_auth_header(admin_token)
    )
    assert resp.status_code == 409


def test_refund_unknown_transaction_returns_404(client, db_path):
    _, admin_token = _make_admin(db_path, client, "0933300012")
    resp = client.post(
        "/admin/transactions/does-not-exist/refund", headers=_auth_header(admin_token)
    )
    assert resp.status_code == 404


def test_stale_pending_requires_admin(client):
    _, token = _register_and_get_token(client, "0933300013")
    resp = client.get("/admin/transactions/stale-pending", headers=_auth_header(token))
    assert resp.status_code == 403


def test_stale_pending_lists_old_pending_transactions(client, db_path):
    _, admin_token = _make_admin(db_path, client, "0933300014")
    _, user_token = _register_and_get_token(client, "0933300015")
    checkout = client.post(
        "/payment/checkout",
        json={"tier": "basic", "billing_cycle": "monthly"},
        headers=_auth_header(user_token),
    ).get_json()

    # Chưa quá 30 phút -> chưa xuất hiện trong danh sách stale
    resp_fresh = client.get(
        "/admin/transactions/stale-pending", headers=_auth_header(admin_token)
    )
    assert resp_fresh.get_json() == []

    conn = models._connect(db_path)
    try:
        old_time = (datetime.utcnow() - timedelta(minutes=45)).isoformat()
        conn.execute(
            "UPDATE payment_transaction SET created_at = ? WHERE id = ?",
            (old_time, checkout["transaction_id"]),
        )
        conn.commit()
    finally:
        conn.close()

    resp_stale = client.get(
        "/admin/transactions/stale-pending", headers=_auth_header(admin_token)
    )
    stale_ids = [t["id"] for t in resp_stale.get_json()]
    assert checkout["transaction_id"] in stale_ids
