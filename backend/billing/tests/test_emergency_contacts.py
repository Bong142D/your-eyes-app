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


def test_add_and_list_emergency_contacts(client):
    _, token = _register_and_get_token(client, "0911100001")
    resp = client.post(
        "/emergency-contacts", json={"name": "Mẹ", "phone": "0911111111"},
        headers=_auth_header(token),
    )
    assert resp.status_code == 201
    assert resp.get_json()["contact_id"]

    list_resp = client.get("/emergency-contacts", headers=_auth_header(token))
    contacts = list_resp.get_json()
    assert len(contacts) == 1
    assert contacts[0]["name"] == "Mẹ"
    assert contacts[0]["phone"] == "0911111111"
    assert contacts[0]["is_primary"] is False


def test_add_contact_without_token_returns_401(client):
    resp = client.post("/emergency-contacts", json={"name": "Mẹ", "phone": "0911111111"})
    assert resp.status_code == 401


def test_add_contact_missing_fields_returns_400(client):
    _, token = _register_and_get_token(client, "0911100002")
    resp = client.post(
        "/emergency-contacts", json={"name": "Mẹ"}, headers=_auth_header(token)
    )
    assert resp.status_code == 400


def test_delete_contact(client):
    _, token = _register_and_get_token(client, "0911100003")
    add_resp = client.post(
        "/emergency-contacts", json={"name": "Anh", "phone": "0911222222"},
        headers=_auth_header(token),
    )
    contact_id = add_resp.get_json()["contact_id"]

    del_resp = client.delete(f"/emergency-contacts/{contact_id}", headers=_auth_header(token))
    assert del_resp.status_code == 200
    assert del_resp.get_json()["message"]

    contacts = client.get("/emergency-contacts", headers=_auth_header(token)).get_json()
    assert contacts == []


def test_delete_other_accounts_contact_returns_404(client):
    _, token_a = _register_and_get_token(client, "0911100004")
    add_resp = client.post(
        "/emergency-contacts", json={"name": "Mẹ", "phone": "0911111111"},
        headers=_auth_header(token_a),
    )
    contact_id = add_resp.get_json()["contact_id"]

    _, token_b = _register_and_get_token(client, "0911100005")
    del_resp = client.delete(f"/emergency-contacts/{contact_id}", headers=_auth_header(token_b))
    assert del_resp.status_code == 404


def test_add_contact_as_primary(client):
    _, token = _register_and_get_token(client, "0911100006")
    resp = client.post(
        "/emergency-contacts", json={"name": "Mẹ", "phone": "0911111111", "is_primary": True},
        headers=_auth_header(token),
    )
    assert resp.status_code == 201
    contacts = client.get("/emergency-contacts", headers=_auth_header(token)).get_json()
    assert contacts[0]["is_primary"] is True


def test_only_one_primary_contact_at_a_time(client):
    _, token = _register_and_get_token(client, "0911100007")
    add1 = client.post(
        "/emergency-contacts", json={"name": "Mẹ", "phone": "0911111111", "is_primary": True},
        headers=_auth_header(token),
    )
    contact1_id = add1.get_json()["contact_id"]
    client.post(
        "/emergency-contacts", json={"name": "Anh", "phone": "0911222222", "is_primary": True},
        headers=_auth_header(token),
    )

    contacts = client.get("/emergency-contacts", headers=_auth_header(token)).get_json()
    primaries = [c for c in contacts if c["is_primary"]]
    assert len(primaries) == 1
    assert primaries[0]["name"] == "Anh"

    # Liên hệ đầu tiên không còn là primary nữa
    contact1 = next(c for c in contacts if c["id"] == contact1_id)
    assert contact1["is_primary"] is False


def test_update_contact_to_set_primary(client):
    _, token = _register_and_get_token(client, "0911100008")
    add_resp = client.post(
        "/emergency-contacts", json={"name": "Mẹ", "phone": "0911111111"},
        headers=_auth_header(token),
    )
    contact_id = add_resp.get_json()["contact_id"]

    patch_resp = client.patch(
        f"/emergency-contacts/{contact_id}", json={"is_primary": True},
        headers=_auth_header(token),
    )
    assert patch_resp.status_code == 200
    assert patch_resp.get_json()["message"]

    contacts = client.get("/emergency-contacts", headers=_auth_header(token)).get_json()
    assert contacts[0]["is_primary"] is True


def test_update_unknown_contact_returns_404(client):
    _, token = _register_and_get_token(client, "0911100009")
    resp = client.patch(
        "/emergency-contacts/does-not-exist", json={"is_primary": True},
        headers=_auth_header(token),
    )
    assert resp.status_code == 404
