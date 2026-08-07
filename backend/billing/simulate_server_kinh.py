"""Giả lập Server Kính gọi vào billing-service qua URL công khai (vd. ngrok) — dùng để tự
kiểm tra kết nối Internet + đúng hợp đồng API khi đội Server Kính thật chưa sẵn sàng test.

Script này CHỈ đóng vai Server Kính (gọi S2S vào backend) — không đóng vai app điện thoại,
không tự đăng ký/liên kết account. Trước khi chạy, serial dùng để test phải đã được LIÊN KẾT
với 1 account qua app thật (đúng thực tế: Server Kính không tạo account/thiết bị).

Cách dùng:
    python simulate_server_kinh.py --base-url https://xxx.ngrok-free.dev --serial YE-DEMO-0006 --all
    python simulate_server_kinh.py --base-url ... --serial ... --call-emergency
    python simulate_server_kinh.py --base-url ... --serial ... --call-contact "mẹ"
    python simulate_server_kinh.py --base-url ... --serial ... --navigate-home
    python simulate_server_kinh.py --base-url ... --serial ... --book-grab-home
    python simulate_server_kinh.py --base-url ... --serial ... --sos

Yêu cầu chuẩn bị trước (làm qua app thật trên điện thoại, KHÔNG phải script này):
    - --call-emergency / --sos  cần account đã có >=1 emergency-contact (is_primary=true).
    - --navigate-home / --book-grab-home  cần account đã lưu saved_place place_type='home'
      (POST /saved-places qua app, hoặc tự gọi bằng token người dùng nếu bạn có).
Thiếu chuẩn bị vẫn chạy được — script sẽ nhận đúng lỗi backend trả về (404), đó cũng là 1
kết quả test hợp lệ (xác nhận backend validate đúng), không phải lỗi của script.
"""
import argparse
import sys
import time
import uuid

import requests

# Console Windows mặc định dùng cp1252, không encode được tiếng Việt có dấu -> crash khi print.
# PowerShell/cmd đọc UTF-8 tốt hơn khi stream đã khai báo đúng, reconfigure an toàn trên
# Python 3.7+, bỏ qua nếu chạy trên môi trường không hỗ trợ (vd. một số IDE runner cũ).
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

DEFAULT_TIMEOUT = 10


def _headers(internal_api_key):
    return {"Authorization": f"Bearer {internal_api_key}", "Content-Type": "application/json"}


def _now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def check_reachable(base_url):
    print(f"--- Kiểm tra kết nối tới {base_url} ---")
    try:
        resp = requests.get(f"{base_url}/health", timeout=DEFAULT_TIMEOUT)
        ok = resp.status_code == 200
        print(("OK " if ok else "LOI"), resp.status_code, resp.text)
        return ok
    except requests.RequestException as exc:
        print("LOI Khong ket noi duoc:", exc)
        return False


def dispatch_action(base_url, internal_api_key, serial, action, params):
    request_id = f"sim-{action}-{uuid.uuid4().hex[:8]}"
    body = {
        "device_id": serial, "request_id": request_id, "action": action,
        "params": params, "timestamp_utc": _now_iso(),
    }
    print(f"\n--- Dispatch action={action} request_id={request_id} ---")
    try:
        resp = requests.post(
            f"{base_url}/internal/api/v1/actions/dispatch",
            json=body, headers=_headers(internal_api_key), timeout=DEFAULT_TIMEOUT,
        )
    except requests.RequestException as exc:
        print("LOI Khong goi duoc:", exc)
        return request_id, None
    try:
        print(resp.status_code, resp.json())
    except ValueError:
        print(resp.status_code, resp.text)
    return request_id, resp


def poll_result(base_url, internal_api_key, request_id):
    print(f"--- Poll ket qua cho request_id={request_id} ---")
    resp = requests.get(
        f"{base_url}/internal/api/v1/actions/{request_id}/result",
        headers=_headers(internal_api_key), timeout=DEFAULT_TIMEOUT,
    )
    try:
        print(resp.status_code, resp.json())
    except ValueError:
        print(resp.status_code, resp.text)
    return resp


def test_call_emergency_contact(base_url, key, serial):
    print("\n=== 1. Goi khan cap cho lien he da luu (call_emergency_contact) ===")
    print("Yeu cau: account cua serial nay da co emergency-contact is_primary=true.")
    request_id, _ = dispatch_action(base_url, key, serial, "call_emergency_contact", {})
    print("-> Kiem tra tren dien thoai that: action co xuat hien qua")
    print("   GET /devices/{id}/pending-actions va app co tu goi khong.")
    return request_id


def test_call_contact(base_url, key, serial, query):
    print(f"\n=== 2. Goi lien he bat ky theo ten (call_contact: '{query}') ===")
    request_id, _ = dispatch_action(base_url, key, serial, "call_contact", {"contact_query": query})
    print("-> App that se tu tim trong danh ba may; neu khong co thi phai tu POST")
    print("   .../report status=no_match, KHONG duoc ep goi.")
    return request_id


def test_navigate_home(base_url, key, serial):
    print("\n=== 3. Chi duong Google Maps ve nha (navigate, place=home) ===")
    print("Yeu cau: account da luu saved_place place_type='home'.")
    request_id, _ = dispatch_action(base_url, key, serial, "navigate", {"place": "home"})
    return request_id


def test_book_grab_home(base_url, key, serial):
    print("\n=== 4. Dat Grab ve nha (book_grab, place=home) ===")
    print("Yeu cau: da luu saved_place 'home'. App se mo deep-link Grab, KHONG co gia/tai xe")
    print("tra ve (da chot 2026-08-03: chi deep-link, khong dung Grab Partner API).")
    request_id, _ = dispatch_action(base_url, key, serial, "book_grab", {"place": "home"})
    return request_id


def test_sos_trigger(base_url, key, serial, lat, lng, yes):
    print("\n=== 5. Kich hoat SOS (kinh tu dem du so lan nhan) ===")
    print("CANH BAO: neu Twilio da cau hinh that tren server, lenh nay gui SMS + GOI DIEN")
    print("THAT toi so dien thoai lien he khan cap is_primary cua account. Chi chay khi da")
    print("san sang nhan cuoc goi/tin nhan that, hoac dung so cua chinh ban de test.")
    if not yes:
        confirm = input("Go 'yes' de tiep tuc, Enter de huy: ")
        if confirm.strip().lower() != "yes":
            print("Da huy.")
            return None
    body = {
        "device_id": serial, "location": {"latitude": lat, "longitude": lng},
        "timestamp_utc": _now_iso(),
    }
    try:
        resp = requests.post(
            f"{base_url}/internal/api/v1/sos/trigger", json=body, headers=_headers(key),
            timeout=DEFAULT_TIMEOUT,
        )
    except requests.RequestException as exc:
        print("LOI Khong goi duoc:", exc)
        return None
    try:
        print(resp.status_code, resp.json())
    except ValueError:
        print(resp.status_code, resp.text)
    print("-> Kiem tra: SMS toi may lien he khan cap (kem link xem vi tri), robocall doc")
    print("   thong bao khan cap, va action 'call_emergency_contact' (params.sos=true)")
    print("   xuat hien qua GET /devices/{id}/pending-actions tren dien thoai chinh chu.")
    return resp


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--base-url", required=True,
        help="URL cong khai cua billing-service, vd. https://xxx.ngrok-free.dev",
    )
    parser.add_argument(
        "--serial", required=True, help="serial_number cua kinh da link voi account tren app that"
    )
    parser.add_argument(
        "--internal-api-key", default="dev-internal-key",
        help="INTERNAL_API_KEY (mac dinh dung gia tri dev)",
    )
    parser.add_argument("--all", action="store_true", help="Chay lan luot ca 5 kich ban")
    parser.add_argument("--call-emergency", action="store_true")
    parser.add_argument("--call-contact", metavar="TEN", help='vd. --call-contact "me"')
    parser.add_argument("--navigate-home", action="store_true")
    parser.add_argument("--book-grab-home", action="store_true")
    parser.add_argument("--sos", action="store_true")
    parser.add_argument("--yes", action="store_true", help="Bo qua xac nhan truoc khi goi --sos")
    parser.add_argument("--lat", type=float, default=10.776889)
    parser.add_argument("--lng", type=float, default=106.700833)
    args = parser.parse_args()

    if not check_reachable(args.base_url):
        sys.exit(1)

    ran_any = False
    if args.all or args.call_emergency:
        test_call_emergency_contact(args.base_url, args.internal_api_key, args.serial)
        ran_any = True
    if args.all or args.call_contact:
        test_call_contact(
            args.base_url, args.internal_api_key, args.serial, args.call_contact or "me"
        )
        ran_any = True
    if args.all or args.navigate_home:
        test_navigate_home(args.base_url, args.internal_api_key, args.serial)
        ran_any = True
    if args.all or args.book_grab_home:
        test_book_grab_home(args.base_url, args.internal_api_key, args.serial)
        ran_any = True
    if args.all or args.sos:
        test_sos_trigger(
            args.base_url, args.internal_api_key, args.serial, args.lat, args.lng, args.yes
        )
        ran_any = True

    if not ran_any:
        print(
            "Chua chon kich ban nao — dung --all hoac 1 trong cac co "
            "--call-emergency/--call-contact/--navigate-home/--book-grab-home/--sos. Xem --help."
        )


if __name__ == "__main__":
    main()
