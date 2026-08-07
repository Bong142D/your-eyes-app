def _register_and_verify(client, phone):
    reg = client.post("/accounts/register", json={"phone": phone})
    otp = reg.get_json()["otp"]
    return client.post(
        "/accounts/verify-otp",
        json={"phone": phone, "code": otp, "purpose": "register"},
    )


def test_register_returns_otp_in_dev_env(client):
    resp = client.post("/accounts/register", json={"phone": "0900000001"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["phone"] == "0900000001"
    assert data["otp"]
    assert data["expires_in"] > 0


def test_register_missing_phone_returns_400(client):
    resp = client.post("/accounts/register", json={})
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_register_duplicate_phone_returns_409(client):
    _register_and_verify(client, "0900000002")  # hoàn tất đăng ký trước
    resp = client.post("/accounts/register", json={"phone": "0900000002"})
    assert resp.status_code == 409


def test_register_again_before_verifying_returns_429(client):
    client.post("/accounts/register", json={"phone": "0900000021"})
    resp = client.post("/accounts/register", json={"phone": "0900000021"})
    assert resp.status_code == 429


def test_verify_otp_register_returns_account_id_and_token(client):
    resp = _register_and_verify(client, "0900000003")
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["account_id"]
    assert data["token"]


def test_verify_otp_wrong_code_returns_401(client):
    client.post("/accounts/register", json={"phone": "0900000004"})
    resp = client.post(
        "/accounts/verify-otp",
        json={"phone": "0900000004", "code": "000000", "purpose": "register"},
    )
    assert resp.status_code == 401


def test_login_existing_account_returns_otp(client):
    _register_and_verify(client, "0900000005")
    resp = client.post("/accounts/login", json={"phone": "0900000005"})
    assert resp.status_code == 200
    assert resp.get_json()["otp"]


def test_login_unknown_account_returns_404(client):
    resp = client.post("/accounts/login", json={"phone": "0900000099"})
    assert resp.status_code == 404


def test_login_verify_otp_returns_token(client):
    _register_and_verify(client, "0900000006")
    login = client.post("/accounts/login", json={"phone": "0900000006"})
    otp = login.get_json()["otp"]
    resp = client.post(
        "/accounts/verify-otp",
        json={"phone": "0900000006", "code": otp, "purpose": "login"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["token"]


def test_logout_revokes_token(client):
    verify = _register_and_verify(client, "0900000007")
    token = verify.get_json()["token"]
    resp = client.post("/accounts/logout", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.get_json()["message"]


def test_get_account_returns_profile_info(client):
    verify = _register_and_verify(client, "0900000008")
    token = verify.get_json()["token"]
    resp = client.get("/account", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["id"] == verify.get_json()["account_id"]
    assert data["phone"] == "0900000008"
    assert data["is_admin"] is False
    assert data["created_at"]


def test_get_account_without_token_returns_401(client):
    resp = client.get("/account")
    assert resp.status_code == 401
