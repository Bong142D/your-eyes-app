from datetime import datetime, timedelta

import models


def _setup_linked_device(client, phone, serial):
    reg = client.post("/accounts/register", json={"phone": phone})
    otp = reg.get_json()["otp"]
    verify = client.post(
        "/accounts/verify-otp", json={"phone": phone, "code": otp, "purpose": "register"}
    )
    verify_data = verify.get_json()
    token = verify_data["token"]
    link = client.post(
        "/devices/link", json={"serial_number": serial},
        headers={"Authorization": f"Bearer {token}"},
    )
    return link.get_json()["device_id"], token


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def test_report_location_missing_fields_returns_400(client):
    device_id, _ = _setup_linked_device(client, "0933300101", "YE-TEST-0001")
    resp = client.post(f"/devices/{device_id}/location", json={"lat": 10.0})
    assert resp.status_code == 400


def test_report_location_unknown_device_returns_404(client):
    resp = client.post("/devices/does-not-exist/location", json={"lat": 10.0, "lng": 106.0})
    assert resp.status_code == 404


def test_current_location_without_data_returns_404(client):
    _, token = _setup_linked_device(client, "0933300102", "YE-TEST-0002")
    resp = client.get("/location/current", headers=_auth_header(token))
    assert resp.status_code == 404


def test_current_location_single_point_is_stationary(client):
    device_id, token = _setup_linked_device(client, "0933300103", "YE-TEST-0003")
    client.post(f"/devices/{device_id}/location", json={"lat": 10.7769, "lng": 106.7009})

    resp = client.get("/location/current", headers=_auth_header(token))
    data = resp.get_json()
    assert data["lat"] == 10.7769
    assert data["status"] == "Đứng yên"


def test_current_location_far_apart_points_is_moving(client):
    device_id, token = _setup_linked_device(client, "0933300104", "YE-TEST-0004")
    client.post(f"/devices/{device_id}/location", json={"lat": 10.7769, "lng": 106.7009})
    # Điểm thứ 2 cách xa hơn 20m (khoảng cách ~vài trăm mét theo lat/lng lệch 0.001 độ)
    client.post(f"/devices/{device_id}/location", json={"lat": 10.7779, "lng": 106.7019})

    resp = client.get("/location/current", headers=_auth_header(token))
    assert resp.get_json()["status"] == "Đang di chuyển"


def test_current_location_close_points_is_stationary(client):
    device_id, token = _setup_linked_device(client, "0933300105", "YE-TEST-0005")
    client.post(f"/devices/{device_id}/location", json={"lat": 10.7769000, "lng": 106.7009000})
    # Lệch cực nhỏ (~1m), vẫn coi là đứng yên
    client.post(f"/devices/{device_id}/location", json={"lat": 10.7769010, "lng": 106.7009000})

    resp = client.get("/location/current", headers=_auth_header(token))
    assert resp.get_json()["status"] == "Đứng yên"


def test_purge_old_location_logs(tmp_path):
    db_path = str(tmp_path / "test.db")
    models.init_db(db_path)
    account_id = models.create_account(db_path, "0933300106")
    models.add_catalog_serial(db_path, "YE-PURGE-0001")
    device_id = models.link_device(db_path, account_id, "YE-PURGE-0001")

    conn = models._connect(db_path)
    try:
        old_time = (datetime.utcnow() - timedelta(days=40)).isoformat()
        conn.execute(
            "INSERT INTO location_log (id, account_id, lat, lng, recorded_at) "
            "VALUES ('old-1', ?, 10.0, 106.0, ?)",
            (account_id, old_time),
        )
        conn.commit()
    finally:
        conn.close()

    models.report_location(db_path, device_id, 10.7769, 106.7009)  # điểm mới, không bị xoá

    deleted = models.purge_old_location_logs(db_path)
    assert deleted == 1
    remaining = models.get_current_location(db_path, account_id)
    assert remaining["lat"] == 10.7769
