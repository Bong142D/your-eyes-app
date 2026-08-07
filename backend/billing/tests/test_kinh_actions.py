import app as billing_app


def _internal_headers():
    return {"Authorization": f"Bearer {billing_app.INTERNAL_API_KEY}"}


# ---------------------------------------------------------------------------
# POST /devices/{device_id}/push-token
# ---------------------------------------------------------------------------

def _link_and_get_ids(client, phone, serial):
    reg = client.post("/accounts/register", json={"phone": phone})
    otp = reg.get_json()["otp"]
    verify = client.post(
        "/accounts/verify-otp", json={"phone": phone, "code": otp, "purpose": "register"}
    )
    token = verify.get_json()["token"]
    link = client.post(
        "/devices/link", json={"serial_number": serial},
        headers={"Authorization": f"Bearer {token}"},
    )
    device_id = link.get_json()["device_id"]
    return token, device_id


def _setup_home_place(client, token, address="Chợ Bến Thành"):
    """navigate/book_grab (quyết định 2026-08-03) chỉ nhận params.place đã lưu sẵn — test nào
    dispatch 2 action này đều cần gọi hàm này trước để có 'home' cho account."""
    client.post(
        "/saved-places",
        json={"place_type": "home", "lat": 10.0, "lng": 106.0, "address": address},
        headers={"Authorization": f"Bearer {token}"},
    )


def test_register_push_token_without_token_returns_401(client):
    _, device_id = _link_and_get_ids(client, "0955500310", "YE-TEST-0001")
    resp = client.post(
        f"/devices/{device_id}/push-token",
        json={"platform": "android", "push_token": "tok-1"},
    )
    assert resp.status_code == 401


def test_register_push_token_missing_fields_returns_400(client):
    token, device_id = _link_and_get_ids(client, "0955500311", "YE-TEST-0002")
    resp = client.post(
        f"/devices/{device_id}/push-token",
        json={"platform": "android"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


def test_register_push_token_success(client):
    token, device_id = _link_and_get_ids(client, "0955500312", "YE-TEST-0003")
    resp = client.post(
        f"/devices/{device_id}/push-token",
        json={"platform": "android", "push_token": "tok-abc"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# POST /internal/api/v1/actions/dispatch
# ---------------------------------------------------------------------------

def test_dispatch_without_internal_key_returns_401(client, monkeypatch):
    # Middleware S2S bỏ qua kiểm tra khi BILLING_ENV=dev (quyết định 2026-08-01, demo Server
    # Kính) — test hành vi enforce thật phải giả lập production.
    monkeypatch.setenv("BILLING_ENV", "production")
    resp = client.post(
        "/internal/api/v1/actions/dispatch",
        json={
            "device_id": "YE-TEST-0001", "request_id": "r1", "action": "navigate",
            "params": {"place": "home"},
            "timestamp_utc": "2026-08-01T10:00:00Z",
        },
    )
    assert resp.status_code == 401


def test_dispatch_missing_fields_returns_400(client):
    resp = client.post(
        "/internal/api/v1/actions/dispatch",
        json={"device_id": "YE-TEST-0001", "action": "navigate"},
        headers=_internal_headers(),
    )
    assert resp.status_code == 400


def test_dispatch_call_contact_missing_query_returns_400(client):
    resp = client.post(
        "/internal/api/v1/actions/dispatch",
        json={
            "device_id": "YE-TEST-0001", "request_id": "r2", "action": "call_contact",
            "params": {}, "timestamp_utc": "2026-08-01T10:00:00Z",
        },
        headers=_internal_headers(),
    )
    assert resp.status_code == 400


def test_dispatch_navigate_missing_place_returns_400(client):
    resp = client.post(
        "/internal/api/v1/actions/dispatch",
        json={
            "device_id": "YE-TEST-0001", "request_id": "r3", "action": "navigate",
            "params": {}, "timestamp_utc": "2026-08-01T10:00:00Z",
        },
        headers=_internal_headers(),
    )
    assert resp.status_code == 400


def test_dispatch_unknown_device_returns_404(client):
    resp = client.post(
        "/internal/api/v1/actions/dispatch",
        json={
            "device_id": "does-not-exist", "request_id": "r4", "action": "navigate",
            "params": {"place": "home"},
            "timestamp_utc": "2026-08-01T10:00:00Z",
        },
        headers=_internal_headers(),
    )
    assert resp.status_code == 404


def test_dispatch_navigate_unknown_place_returns_404(client):
    _link_and_get_ids(client, "0955500325", "YE-TEST-0001")  # chưa setup saved place nào
    resp = client.post(
        "/internal/api/v1/actions/dispatch",
        json={
            "device_id": "YE-TEST-0001", "request_id": "r4b", "action": "navigate",
            "params": {"place": "home"}, "timestamp_utc": "2026-08-01T10:00:00Z",
        },
        headers=_internal_headers(),
    )
    assert resp.status_code == 404


def test_dispatch_call_emergency_contact_without_primary_returns_404(client):
    _link_and_get_ids(client, "0955500320", "YE-TEST-0001")  # không thêm liên hệ khẩn cấp
    resp = client.post(
        "/internal/api/v1/actions/dispatch",
        json={
            "device_id": "YE-TEST-0001", "request_id": "r5", "action": "call_emergency_contact",
            "params": {}, "timestamp_utc": "2026-08-01T10:00:00Z",
        },
        headers=_internal_headers(),
    )
    assert resp.status_code == 404


def test_dispatch_without_push_token_returns_200_no_push_token(client):
    token, device_id = _link_and_get_ids(client, "0955500321", "YE-TEST-0002")
    client.post(
        "/emergency-contacts", json={"name": "Mẹ", "phone": "0911111111", "is_primary": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = client.post(
        "/internal/api/v1/actions/dispatch",
        json={
            "device_id": "YE-TEST-0002", "request_id": "r6", "action": "call_emergency_contact",
            "params": {}, "timestamp_utc": "2026-08-01T10:00:00Z",
        },
        headers=_internal_headers(),
    )
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "no_push_token"


def test_dispatch_call_emergency_contact_with_push_token_returns_202(client):
    token, device_id = _link_and_get_ids(client, "0955500322", "YE-TEST-0003")
    client.post(
        "/emergency-contacts", json={"name": "Mẹ", "phone": "0911111111", "is_primary": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    client.post(
        f"/devices/{device_id}/push-token",
        json={"platform": "android", "push_token": "tok-xyz"},
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = client.post(
        "/internal/api/v1/actions/dispatch",
        json={
            "device_id": "YE-TEST-0003", "request_id": "r7", "action": "call_emergency_contact",
            "params": {}, "timestamp_utc": "2026-08-01T10:00:00Z",
        },
        headers=_internal_headers(),
    )
    assert resp.status_code == 202
    assert resp.get_json()["status"] == "dispatched"


def test_dispatch_is_idempotent_by_request_id(client):
    token, device_id = _link_and_get_ids(client, "0955500323", "YE-TEST-0004")
    _setup_home_place(client, token)
    client.post(
        f"/devices/{device_id}/push-token",
        json={"platform": "ios", "push_token": "tok-ios"},
        headers={"Authorization": f"Bearer {token}"},
    )
    body = {
        "device_id": "YE-TEST-0004", "request_id": "r8-repeat", "action": "navigate",
        "params": {"place": "home"},
        "timestamp_utc": "2026-08-01T10:00:00Z",
    }
    first = client.post("/internal/api/v1/actions/dispatch", json=body, headers=_internal_headers())
    second = client.post("/internal/api/v1/actions/dispatch", json=body, headers=_internal_headers())
    assert first.status_code == 202
    assert second.status_code == 200
    assert first.get_json()["status"] == second.get_json()["status"] == "dispatched"


# ---------------------------------------------------------------------------
# POST /devices/{device_id}/actions/{request_id}/report
# ---------------------------------------------------------------------------

def test_report_without_token_returns_401(client):
    _, device_id = _link_and_get_ids(client, "0955500330", "YE-TEST-0005")
    resp = client.post(
        f"/devices/{device_id}/actions/some-request/report", json={"status": "done"}
    )
    assert resp.status_code == 401


def test_report_invalid_status_returns_400(client):
    token, device_id = _link_and_get_ids(client, "0955500331", "YE-TEST-0001")
    resp = client.post(
        f"/devices/{device_id}/actions/some-request/report",
        json={"status": "bogus"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


def test_report_unknown_request_id_returns_404(client):
    token, device_id = _link_and_get_ids(client, "0955500332", "YE-TEST-0002")
    resp = client.post(
        f"/devices/{device_id}/actions/does-not-exist/report",
        json={"status": "done"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


def test_report_no_match_for_call_contact(client):
    token, device_id = _link_and_get_ids(client, "0955500333", "YE-TEST-0003")
    client.post(
        f"/devices/{device_id}/push-token",
        json={"platform": "android", "push_token": "tok-3"},
        headers={"Authorization": f"Bearer {token}"},
    )
    client.post(
        "/internal/api/v1/actions/dispatch",
        json={
            "device_id": "YE-TEST-0003", "request_id": "r9", "action": "call_contact",
            "params": {"contact_query": "chú Ba"}, "timestamp_utc": "2026-08-01T10:00:00Z",
        },
        headers=_internal_headers(),
    )
    resp = client.post(
        f"/devices/{device_id}/actions/r9/report",
        json={"status": "no_match", "detail": "Không tìm thấy 'chú Ba' trong danh bạ."},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


def test_report_can_be_called_multiple_times_for_book_grab_progress(client):
    token, device_id = _link_and_get_ids(client, "0955500334", "YE-TEST-0004")
    _setup_home_place(client, token)
    client.post(
        f"/devices/{device_id}/push-token",
        json={"platform": "android", "push_token": "tok-4"},
        headers={"Authorization": f"Bearer {token}"},
    )
    client.post(
        "/internal/api/v1/actions/dispatch",
        json={
            "device_id": "YE-TEST-0004", "request_id": "r10", "action": "book_grab",
            "params": {"place": "home"},
            "timestamp_utc": "2026-08-01T10:00:00Z",
        },
        headers=_internal_headers(),
    )
    for status in ("in_progress", "in_progress", "done"):
        resp = client.post(
            f"/devices/{device_id}/actions/r10/report",
            json={"status": status, "detail": "cập nhật trạng thái Grab"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# GET /internal/api/v1/actions/{request_id}/result
# ---------------------------------------------------------------------------

def test_get_action_result_without_internal_key_returns_401(client, monkeypatch):
    monkeypatch.setenv("BILLING_ENV", "production")
    resp = client.get("/internal/api/v1/actions/some-request/result")
    assert resp.status_code == 401


def test_get_action_result_unknown_request_id_returns_404(client):
    resp = client.get(
        "/internal/api/v1/actions/does-not-exist/result", headers=_internal_headers()
    )
    assert resp.status_code == 404


def test_get_action_result_before_any_report_returns_empty_reports(client):
    token, device_id = _link_and_get_ids(client, "0955500340", "YE-TEST-0005")
    _setup_home_place(client, token)
    client.post(
        f"/devices/{device_id}/push-token",
        json={"platform": "android", "push_token": "tok-5"},
        headers={"Authorization": f"Bearer {token}"},
    )
    client.post(
        "/internal/api/v1/actions/dispatch",
        json={
            "device_id": "YE-TEST-0005", "request_id": "r11", "action": "navigate",
            "params": {"place": "home"},
            "timestamp_utc": "2026-08-01T10:00:00Z",
        },
        headers=_internal_headers(),
    )
    resp = client.get("/internal/api/v1/actions/r11/result", headers=_internal_headers())
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["action"] == "navigate"
    assert body["dispatch_status"] == "dispatched"
    assert body["reports"] == []


def test_get_action_result_returns_report_history_in_order(client):
    token, device_id = _link_and_get_ids(client, "0955500341", "YE-TEST-0001")
    _setup_home_place(client, token)
    client.post(
        f"/devices/{device_id}/push-token",
        json={"platform": "android", "push_token": "tok-6"},
        headers={"Authorization": f"Bearer {token}"},
    )
    client.post(
        "/internal/api/v1/actions/dispatch",
        json={
            "device_id": "YE-TEST-0001", "request_id": "r12", "action": "book_grab",
            "params": {"place": "home"},
            "timestamp_utc": "2026-08-01T10:00:00Z",
        },
        headers=_internal_headers(),
    )
    for status, detail in [("in_progress", "Đã đặt xe"), ("done", "Tài xế đang tới")]:
        client.post(
            f"/devices/{device_id}/actions/r12/report",
            json={"status": status, "detail": detail},
            headers={"Authorization": f"Bearer {token}"},
        )
    resp = client.get("/internal/api/v1/actions/r12/result", headers=_internal_headers())
    body = resp.get_json()
    assert [r["status"] for r in body["reports"]] == ["in_progress", "done"]


# ---------------------------------------------------------------------------
# GET /devices/{device_id}/pending-actions (mới 2026-08-02 — thay kênh push cho Expo Go)
# ---------------------------------------------------------------------------

def test_pending_actions_empty_when_nothing_dispatched(client):
    token, device_id = _link_and_get_ids(client, "0955500350", "YE-TEST-0001")
    resp = client.get(
        f"/devices/{device_id}/pending-actions", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_pending_actions_without_token_returns_401(client):
    _, device_id = _link_and_get_ids(client, "0955500351", "YE-TEST-0002")
    resp = client.get(f"/devices/{device_id}/pending-actions")
    assert resp.status_code == 401


def test_pending_actions_returns_undispatched_action(client):
    token, device_id = _link_and_get_ids(client, "0955500352", "YE-TEST-0003")
    _setup_home_place(client, token, address="Chợ Bến Thành")
    client.post(
        "/internal/api/v1/actions/dispatch",
        json={
            "device_id": "YE-TEST-0003", "request_id": "pending-1", "action": "navigate",
            "params": {"place": "home"},
            "timestamp_utc": "2026-08-01T10:00:00Z",
        },
        headers=_internal_headers(),
    )
    resp = client.get(
        f"/devices/{device_id}/pending-actions", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body) == 1
    assert body[0]["request_id"] == "pending-1"
    assert body[0]["action"] == "navigate"
    assert body[0]["params"]["destination"]["address"] == "Chợ Bến Thành"


def test_pending_actions_disappears_after_report(client):
    token, device_id = _link_and_get_ids(client, "0955500353", "YE-TEST-0004")
    _setup_home_place(client, token)
    client.post(
        "/internal/api/v1/actions/dispatch",
        json={
            "device_id": "YE-TEST-0004", "request_id": "pending-2", "action": "navigate",
            "params": {"place": "home"},
            "timestamp_utc": "2026-08-01T10:00:00Z",
        },
        headers=_internal_headers(),
    )
    client.post(
        f"/devices/{device_id}/actions/pending-2/report",
        json={"status": "cancelled"},
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = client.get(
        f"/devices/{device_id}/pending-actions", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.get_json() == []


def test_pending_actions_only_shows_own_device(client):
    token_a, device_a = _link_and_get_ids(client, "0955500354", "YE-TEST-0005")
    token_b, device_b = _link_and_get_ids(client, "0955500355", "YE-TEST-0004")
    _setup_home_place(client, token_b)
    client.post(
        "/internal/api/v1/actions/dispatch",
        json={
            "device_id": "YE-TEST-0004", "request_id": "pending-3", "action": "navigate",
            "params": {"place": "home"},
            "timestamp_utc": "2026-08-01T10:00:00Z",
        },
        headers=_internal_headers(),
    )
    resp = client.get(
        f"/devices/{device_a}/pending-actions", headers={"Authorization": f"Bearer {token_a}"}
    )
    assert resp.get_json() == []


def test_report_accepts_cancelled_status(client):
    token, device_id = _link_and_get_ids(client, "0955500356", "YE-TEST-0001")
    client.post(
        "/internal/api/v1/actions/dispatch",
        json={
            "device_id": "YE-TEST-0001", "request_id": "pending-4", "action": "call_contact",
            "params": {"contact_query": "mẹ"}, "timestamp_utc": "2026-08-01T10:00:00Z",
        },
        headers=_internal_headers(),
    )
    resp = client.post(
        f"/devices/{device_id}/actions/pending-4/report",
        json={"status": "cancelled"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# /saved-places (quyết định 2026-08-03) — navigate/book_grab chỉ dùng địa điểm đã lưu
# ---------------------------------------------------------------------------

def test_list_saved_places_without_token_returns_401(client):
    resp = client.get("/saved-places")
    assert resp.status_code == 401


def test_list_saved_places_empty_by_default(client):
    reg = client.post("/accounts/register", json={"phone": "0955500360"})
    otp = reg.get_json()["otp"]
    token = client.post(
        "/accounts/verify-otp",
        json={"phone": "0955500360", "code": otp, "purpose": "register"},
    ).get_json()["token"]
    resp = client.get("/saved-places", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.get_json() == []


def _register_token(client, phone):
    reg = client.post("/accounts/register", json={"phone": phone})
    otp = reg.get_json()["otp"]
    return client.post(
        "/accounts/verify-otp", json={"phone": phone, "code": otp, "purpose": "register"}
    ).get_json()["token"]


def test_add_saved_place_invalid_place_type_returns_400(client):
    token = _register_token(client, "0955500361")
    resp = client.post(
        "/saved-places",
        json={"place_type": "office", "lat": 10.0, "lng": 106.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


def test_add_saved_place_other_without_label_returns_400(client):
    token = _register_token(client, "0955500362")
    resp = client.post(
        "/saved-places",
        json={"place_type": "other", "lat": 10.0, "lng": 106.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


def test_add_saved_place_home_success_and_list(client):
    token = _register_token(client, "0955500363")
    resp = client.post(
        "/saved-places",
        json={"place_type": "home", "lat": 10.77, "lng": 106.70, "address": "123 Lê Lợi"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    places = client.get("/saved-places", headers={"Authorization": f"Bearer {token}"}).get_json()
    assert len(places) == 1
    assert places[0]["place_type"] == "home"
    assert places[0]["address"] == "123 Lê Lợi"


def test_add_saved_place_home_twice_replaces_old_one(client):
    token = _register_token(client, "0955500364")
    client.post(
        "/saved-places",
        json={"place_type": "home", "lat": 10.0, "lng": 106.0, "address": "Nhà cũ"},
        headers={"Authorization": f"Bearer {token}"},
    )
    client.post(
        "/saved-places",
        json={"place_type": "home", "lat": 11.0, "lng": 107.0, "address": "Nhà mới"},
        headers={"Authorization": f"Bearer {token}"},
    )
    places = client.get("/saved-places", headers={"Authorization": f"Bearer {token}"}).get_json()
    homes = [p for p in places if p["place_type"] == "home"]
    assert len(homes) == 1
    assert homes[0]["address"] == "Nhà mới"


def test_add_saved_place_other_allows_multiple_with_labels(client):
    token = _register_token(client, "0955500365")
    client.post(
        "/saved-places",
        json={"place_type": "other", "label": "Công ty", "lat": 10.0, "lng": 106.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    client.post(
        "/saved-places",
        json={"place_type": "other", "label": "Trường học", "lat": 11.0, "lng": 107.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    places = client.get("/saved-places", headers={"Authorization": f"Bearer {token}"}).get_json()
    assert len(places) == 2


def test_update_saved_place_not_found_returns_404(client):
    token = _register_token(client, "0955500366")
    resp = client.patch(
        "/saved-places/does-not-exist",
        json={"label": "x"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


def test_delete_saved_place_not_found_returns_404(client):
    token = _register_token(client, "0955500367")
    resp = client.delete(
        "/saved-places/does-not-exist", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 404


def test_delete_saved_place_success(client):
    token = _register_token(client, "0955500368")
    create = client.post(
        "/saved-places",
        json={"place_type": "home", "lat": 10.0, "lng": 106.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    place_id = create.get_json()["place_id"]
    resp = client.delete(
        f"/saved-places/{place_id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert client.get("/saved-places", headers={"Authorization": f"Bearer {token}"}).get_json() == []


def test_dispatch_navigate_without_saved_home_returns_404(client):
    _link_and_get_ids(client, "0955500369", "YE-TEST-0002")
    resp = client.post(
        "/internal/api/v1/actions/dispatch",
        json={
            "device_id": "YE-TEST-0002", "request_id": "no-home-1", "action": "navigate",
            "params": {"place": "home"}, "timestamp_utc": "2026-08-01T10:00:00Z",
        },
        headers=_internal_headers(),
    )
    assert resp.status_code == 404


def test_dispatch_book_grab_with_other_place_label(client):
    token, device_id = _link_and_get_ids(client, "0955500370", "YE-TEST-0003")
    client.post(
        "/saved-places",
        json={"place_type": "other", "label": "Công ty", "lat": 10.5, "lng": 106.5,
              "address": "Toà nhà ABC"},
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = client.post(
        "/internal/api/v1/actions/dispatch",
        json={
            "device_id": "YE-TEST-0003", "request_id": "office-1", "action": "book_grab",
            "params": {"place": "Công ty"}, "timestamp_utc": "2026-08-01T10:00:00Z",
        },
        headers=_internal_headers(),
    )
    assert resp.status_code in (200, 202)
    pending = client.get(
        f"/devices/{device_id}/pending-actions", headers={"Authorization": f"Bearer {token}"}
    ).get_json()
    assert pending[0]["params"]["destination"]["address"] == "Toà nhà ABC"
