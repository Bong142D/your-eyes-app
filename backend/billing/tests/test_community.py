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


def _seed_group_and_event(db_path):
    import models

    group_id = models.add_community_group(db_path, "Người mới dùng kính", "Mô tả nhóm")
    event_id = models.add_community_event(
        db_path, "Gặp mặt cộng đồng TP.HCM", "2026-08-03T14:00:00", "Q.1, TP.HCM"
    )
    return group_id, event_id


def test_list_groups_returns_zero_members_initially(client, db_path):
    group_id, _ = _seed_group_and_event(db_path)
    resp = client.get("/community/groups")
    assert resp.status_code == 200
    groups = resp.get_json()
    assert len(groups) == 1
    assert groups[0]["name"] == "Người mới dùng kính"
    assert groups[0]["member_count"] == 0


def test_join_group_increments_member_count(client, db_path):
    group_id, _ = _seed_group_and_event(db_path)
    _, token = _register_and_get_token(client, "0966600001")
    resp = client.post(f"/community/groups/{group_id}/join", headers=_auth_header(token))
    assert resp.status_code == 200
    assert resp.get_json()["message"]

    groups = client.get("/community/groups").get_json()
    assert groups[0]["member_count"] == 1


def test_join_group_without_token_returns_401(client, db_path):
    group_id, _ = _seed_group_and_event(db_path)
    resp = client.post(f"/community/groups/{group_id}/join")
    assert resp.status_code == 401


def test_join_unknown_group_returns_404(client):
    _, token = _register_and_get_token(client, "0966600002")
    resp = client.post("/community/groups/does-not-exist/join", headers=_auth_header(token))
    assert resp.status_code == 404


def test_join_group_twice_is_idempotent(client, db_path):
    group_id, _ = _seed_group_and_event(db_path)
    _, token = _register_and_get_token(client, "0966600003")
    client.post(f"/community/groups/{group_id}/join", headers=_auth_header(token))
    client.post(f"/community/groups/{group_id}/join", headers=_auth_header(token))
    groups = client.get("/community/groups").get_json()
    assert groups[0]["member_count"] == 1


def test_create_post_shows_immediately_without_moderation(client):
    _, token = _register_and_get_token(client, "0966600004")
    resp = client.post(
        "/community/posts",
        json={"author_name": "Cô Lan", "title": "Cách chỉnh giọng đọc", "content": "Nội dung..."},
        headers=_auth_header(token),
    )
    assert resp.status_code == 201

    posts = client.get("/community/posts").get_json()
    assert len(posts) == 1
    assert posts[0]["author_name"] == "Cô Lan"
    assert posts[0]["title"] == "Cách chỉnh giọng đọc"


def test_create_post_without_token_returns_401(client):
    resp = client.post(
        "/community/posts", json={"author_name": "X", "title": "T", "content": "C"}
    )
    assert resp.status_code == 401


def test_create_post_missing_fields_returns_400(client):
    _, token = _register_and_get_token(client, "0966600005")
    resp = client.post(
        "/community/posts", json={"title": "T"}, headers=_auth_header(token)
    )
    assert resp.status_code == 400


def test_posts_ordered_newest_first(client):
    _, token = _register_and_get_token(client, "0966600006")
    client.post(
        "/community/posts",
        json={"author_name": "A", "title": "Bài 1", "content": "c1"},
        headers=_auth_header(token),
    )
    client.post(
        "/community/posts",
        json={"author_name": "B", "title": "Bài 2", "content": "c2"},
        headers=_auth_header(token),
    )
    posts = client.get("/community/posts").get_json()
    assert posts[0]["title"] == "Bài 2"
    assert posts[1]["title"] == "Bài 1"


def test_list_events(client, db_path):
    _, event_id = _seed_group_and_event(db_path)
    resp = client.get("/community/events")
    assert resp.status_code == 200
    events = resp.get_json()
    assert len(events) == 1
    assert events[0]["title"] == "Gặp mặt cộng đồng TP.HCM"


def test_save_and_list_saved_events(client, db_path):
    _, event_id = _seed_group_and_event(db_path)
    _, token = _register_and_get_token(client, "0966600007")

    save_resp = client.post(f"/community/events/{event_id}/save", headers=_auth_header(token))
    assert save_resp.status_code == 200
    assert save_resp.get_json()["message"]

    saved = client.get("/community/events/saved", headers=_auth_header(token)).get_json()
    assert len(saved) == 1
    assert saved[0]["title"] == "Gặp mặt cộng đồng TP.HCM"


def test_save_unknown_event_returns_404(client):
    _, token = _register_and_get_token(client, "0966600008")
    resp = client.post("/community/events/does-not-exist/save", headers=_auth_header(token))
    assert resp.status_code == 404


def test_unsave_event(client, db_path):
    _, event_id = _seed_group_and_event(db_path)
    _, token = _register_and_get_token(client, "0966600009")
    client.post(f"/community/events/{event_id}/save", headers=_auth_header(token))

    unsave_resp = client.delete(
        f"/community/events/{event_id}/save", headers=_auth_header(token)
    )
    assert unsave_resp.status_code == 200
    assert unsave_resp.get_json()["message"]

    saved = client.get("/community/events/saved", headers=_auth_header(token)).get_json()
    assert saved == []
