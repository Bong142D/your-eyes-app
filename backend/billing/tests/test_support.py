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


def test_list_support_articles(client, db_path):
    models.add_support_article(db_path, "guide", "Hướng dẫn sử dụng", "Nội dung hướng dẫn")
    models.add_support_article(db_path, "faq", "FAQ", "Nội dung FAQ")

    all_articles = client.get("/support/articles").get_json()
    assert len(all_articles) == 2

    guides = client.get("/support/articles?kind=guide").get_json()
    assert len(guides) == 1
    assert guides[0]["title"] == "Hướng dẫn sử dụng"


def test_create_ticket_bug_report(client):
    _, token = _register_and_get_token(client, "0988800001")
    resp = client.post(
        "/support/tickets",
        json={"category": "bug_report", "description": "Kính không kết nối được Bluetooth"},
        headers=_auth_header(token),
    )
    assert resp.status_code == 201
    assert resp.get_json()["ticket_id"]


def test_create_ticket_invalid_category_returns_400(client):
    _, token = _register_and_get_token(client, "0988800002")
    resp = client.post(
        "/support/tickets",
        json={"category": "not-a-real-category", "description": "..."},
        headers=_auth_header(token),
    )
    assert resp.status_code == 400


def test_create_ticket_missing_description_returns_400(client):
    _, token = _register_and_get_token(client, "0988800003")
    resp = client.post(
        "/support/tickets", json={"category": "bug_report"}, headers=_auth_header(token)
    )
    assert resp.status_code == 400


def test_create_ticket_without_token_returns_401(client):
    resp = client.post(
        "/support/tickets", json={"category": "bug_report", "description": "..."}
    )
    assert resp.status_code == 401


def test_list_own_tickets_only_shows_own(client):
    _, token_a = _register_and_get_token(client, "0988800004")
    client.post(
        "/support/tickets",
        json={"category": "bug_report", "description": "Lỗi của A"},
        headers=_auth_header(token_a),
    )
    _, token_b = _register_and_get_token(client, "0988800005")
    client.post(
        "/support/tickets",
        json={"category": "support_request", "description": "Yêu cầu của B"},
        headers=_auth_header(token_b),
    )

    tickets_a = client.get("/support/tickets", headers=_auth_header(token_a)).get_json()
    assert len(tickets_a) == 1
    assert tickets_a[0]["description"] == "Lỗi của A"
    assert tickets_a[0]["status"] == "open"


def test_admin_can_list_all_tickets_and_update_status(client, db_path):
    account_id, admin_token = _register_and_get_token(client, "0988800006")
    models.set_is_admin(db_path, account_id, True)
    _, user_token = _register_and_get_token(client, "0988800007")
    create_resp = client.post(
        "/support/tickets",
        json={"category": "bug_report", "description": "Lỗi pin"},
        headers=_auth_header(user_token),
    )
    ticket_id = create_resp.get_json()["ticket_id"]

    all_tickets = client.get("/admin/support/tickets", headers=_auth_header(admin_token)).get_json()
    assert len(all_tickets) == 1

    update_resp = client.patch(
        f"/admin/support/tickets/{ticket_id}/status",
        json={"status": "resolved"},
        headers=_auth_header(admin_token),
    )
    assert update_resp.status_code == 200
    assert update_resp.get_json()["message"]

    tickets = client.get("/support/tickets", headers=_auth_header(user_token)).get_json()
    assert tickets[0]["status"] == "resolved"
    assert tickets[0]["resolved_at"] is not None


def test_admin_routes_require_admin(client):
    _, token = _register_and_get_token(client, "0988800008")
    resp = client.get("/admin/support/tickets", headers=_auth_header(token))
    assert resp.status_code == 403


def test_update_unknown_ticket_returns_404(client, db_path):
    account_id, admin_token = _register_and_get_token(client, "0988800009")
    models.set_is_admin(db_path, account_id, True)
    resp = client.patch(
        "/admin/support/tickets/does-not-exist/status",
        json={"status": "resolved"},
        headers=_auth_header(admin_token),
    )
    assert resp.status_code == 404


def test_update_ticket_invalid_status_returns_400(client, db_path):
    account_id, admin_token = _register_and_get_token(client, "0988800010")
    models.set_is_admin(db_path, account_id, True)
    _, user_token = _register_and_get_token(client, "0988800011")
    create_resp = client.post(
        "/support/tickets",
        json={"category": "bug_report", "description": "Lỗi"},
        headers=_auth_header(user_token),
    )
    ticket_id = create_resp.get_json()["ticket_id"]

    resp = client.patch(
        f"/admin/support/tickets/{ticket_id}/status",
        json={"status": "not-a-real-status"},
        headers=_auth_header(admin_token),
    )
    assert resp.status_code == 400


def test_update_ticket_status_notifies_user_by_sms(client, db_path, monkeypatch):
    account_id, admin_token = _register_and_get_token(client, "0988800013")
    models.set_is_admin(db_path, account_id, True)
    _, user_token = _register_and_get_token(client, "0988800014")
    create_resp = client.post(
        "/support/tickets",
        json={"category": "bug_report", "description": "Lỗi pin"},
        headers=_auth_header(user_token),
    )
    ticket_id = create_resp.get_json()["ticket_id"]

    sent = []
    monkeypatch.setattr(
        models, "_send_sms", lambda phone, message: sent.append((phone, message)) or True
    )

    client.patch(
        f"/admin/support/tickets/{ticket_id}/status",
        json={"status": "in_progress"},
        headers=_auth_header(admin_token),
    )

    assert len(sent) == 1
    assert sent[0][0] == "0988800014"
    assert "Đang xử lý" in sent[0][1]


def test_update_ticket_status_no_sms_if_status_unchanged(client, db_path, monkeypatch):
    account_id, admin_token = _register_and_get_token(client, "0988800015")
    models.set_is_admin(db_path, account_id, True)
    _, user_token = _register_and_get_token(client, "0988800016")
    create_resp = client.post(
        "/support/tickets",
        json={"category": "bug_report", "description": "Lỗi pin"},
        headers=_auth_header(user_token),
    )
    ticket_id = create_resp.get_json()["ticket_id"]

    sent = []
    monkeypatch.setattr(
        models, "_send_sms", lambda phone, message: sent.append((phone, message)) or True
    )

    client.patch(
        f"/admin/support/tickets/{ticket_id}/status",
        json={"status": "open"},  # đã là "open" sẵn — không đổi
        headers=_auth_header(admin_token),
    )

    assert sent == []


def test_hotline_call_log(client):
    resp = client.post("/support/hotline/call-log")
    assert resp.status_code == 200
    assert resp.get_json()["message"]

    _, token = _register_and_get_token(client, "0988800012")
    resp2 = client.post("/support/hotline/call-log", headers=_auth_header(token))
    assert resp2.status_code == 200
    assert resp2.get_json()["message"]
