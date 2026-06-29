def test_register_returns_account_id_and_token(client):
    resp = client.post("/accounts/register", json={"email": "a@example.com"})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["account_id"]
    assert data["token"] == data["account_id"]


def test_register_missing_email_returns_400(client):
    resp = client.post("/accounts/register", json={})
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_register_duplicate_email_returns_409(client):
    client.post("/accounts/register", json={"email": "dup@example.com"})
    resp = client.post("/accounts/register", json={"email": "dup@example.com"})
    assert resp.status_code == 409


def test_login_existing_account_returns_200(client):
    client.post("/accounts/register", json={"email": "b@example.com"})
    resp = client.post("/accounts/login", json={"email": "b@example.com"})
    assert resp.status_code == 200
    assert resp.get_json()["account_id"]


def test_login_unknown_account_returns_404(client):
    resp = client.post("/accounts/login", json={"email": "nope@example.com"})
    assert resp.status_code == 404