import logging
import os
from datetime import datetime

from flask import Flask, jsonify, request

import models
import tiers

# Bắt buộc phải cấu hình logging thì logger.info() trong models.py (SOS TRIGGERED,
# SIMULATING_SMS, PUSH_NOTIFICATION_SENT...) mới thật sự in ra được — mặc định Python chỉ
# in WARNING trở lên khi chưa có handler nào, nên trước đây các dòng log INFO này biến mất
# hoàn toàn khỏi `docker logs`.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)


def get_db_path():
    path = os.environ.get("BILLING_DB_PATH", "billing_data.db")
    if not os.path.exists(path):
        models.init_db(path)
    return path


def _sync_schema_on_startup():
    """Chạy 1 LẦN lúc process khởi động (không phải mỗi request, khác get_db_path ở trên) —
    quyết định 2026-08-02, sau khi phát hiện DB Docker volume đã tồn tại từ trước khi
    kinh_action_request/kinh_action_report/device_push_token được thêm vào schema.sql, nên các
    bảng đó chưa từng được tạo thật (get_db_path chỉ init_db khi FILE chưa tồn tại, không phải
    khi SCHEMA thiếu bảng mới). models.init_db chỉ chạy CREATE TABLE IF NOT EXISTS — an toàn
    100%, không đụng dữ liệu đã có, dù file đã tồn tại hay chưa. Mỗi lần restart container từ
    giờ tự đồng bộ schema, không cần nhớ chạy tay."""
    models.init_db(get_db_path())


_sync_schema_on_startup()


def is_dev_env():
    # Mặc định coi là dev trừ khi khai báo rõ production — khớp Dockerfile (ENV BILLING_ENV=dev).
    return os.environ.get("BILLING_ENV", "dev") != "production"


def _run_scheduled_retry_failed_notifications():
    try:
        retried = models.retry_failed_notifications(get_db_path())
        if retried:
            logger.info(f"[scheduler] retried {retried} failed Server Kính notification(s)")
    except Exception:
        logger.exception("[scheduler] retry_failed_notifications job lỗi")


def _run_scheduled_check_expiry():
    try:
        checked = models.scan_and_notify_expired_subscriptions(get_db_path())
        if checked:
            logger.info(f"[scheduler] xử lý {checked} subscription vừa hết hạn")
    except Exception:
        logger.exception("[scheduler] scan_and_notify_expired_subscriptions job lỗi")


def _run_scheduled_purge_old_location_logs():
    try:
        purged = models.purge_old_location_logs(get_db_path())
        if purged:
            logger.info(f"[scheduler] xoá {purged} dòng location_log quá hạn retention")
    except Exception:
        logger.exception("[scheduler] purge_old_location_logs job lỗi")


def _start_background_scheduler():
    """Job nền chạy trong process Flask (quyết định 2026-08-02, thay cho phải gọi tay 2 admin
    endpoint /admin/notifications/retry-failed và /admin/subscriptions/check-expiry) — an toàn
    với cấu hình hiện tại (Dockerfile không chỉ định --workers cho gunicorn, mặc định 1 worker,
    nên job không bị gọi trùng). Tắt qua ENV SCHEDULER_ENABLED=false nếu sau này tăng số
    worker (tránh gọi trùng SMS/push) hoặc khi chạy test. Guard theo app.debug/WERKZEUG_RUN_MAIN
    để không khởi động 2 lần nếu ai đó bật Flask debug reloader (hiện __main__ không bật debug,
    chỉ phòng hờ)."""
    if os.environ.get("SCHEDULER_ENABLED", "true").lower() == "false":
        logger.info("[scheduler] SCHEDULER_ENABLED=false — bỏ qua, dùng admin endpoint gọi tay.")
        return None
    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return None
    from apscheduler.schedulers.background import BackgroundScheduler

    scheduler = BackgroundScheduler(daemon=True)
    retry_minutes = int(os.environ.get("RETRY_NOTIFICATIONS_INTERVAL_MINUTES", 5))
    expiry_minutes = int(os.environ.get("CHECK_EXPIRY_INTERVAL_MINUTES", 10))
    purge_minutes = int(os.environ.get("PURGE_LOCATION_LOGS_INTERVAL_MINUTES", 24 * 60))
    scheduler.add_job(
        _run_scheduled_retry_failed_notifications, "interval",
        minutes=retry_minutes, id="retry_failed_notifications",
    )
    scheduler.add_job(
        _run_scheduled_check_expiry, "interval",
        minutes=expiry_minutes, id="check_expiry",
    )
    scheduler.add_job(
        _run_scheduled_purge_old_location_logs, "interval",
        minutes=purge_minutes, id="purge_old_location_logs",
    )
    scheduler.start()
    logger.info(
        f"[scheduler] đã bật — retry-failed-notifications mỗi {retry_minutes} phút, "
        f"check-expiry mỗi {expiry_minutes} phút, purge-location-logs mỗi {purge_minutes} phút."
    )
    return scheduler


_scheduler = _start_background_scheduler()


def get_bearer_token():
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return header[len("Bearer "):]
    return None


# Alias để test/code cũ tham chiếu qua app.INTERNAL_API_KEY — nguồn thật nằm ở models.py vì
# models.py cũng cần key này để tự gọi RA Server Kính (mục 5.1d), tránh định nghĩa 2 nơi.
INTERNAL_API_KEY = models.INTERNAL_API_KEY


def _display_dt(value):
    """Định dạng lại 1 chuỗi ISO (lưu trong DB) thành "yyyy-MM-dd HH:mm:ss" dễ đọc cho app —
    CHỈ áp dụng ở tầng response. Không đụng tới định dạng lưu trữ/so sánh nội bộ trong models.py
    (vẫn giữ ISO để so sánh chuỗi đúng thứ tự thời gian)."""
    if not value:
        return value
    try:
        return datetime.fromisoformat(value).strftime("%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return value


@app.before_request
def _enforce_internal_api_auth():
    """Middleware chung cho MỌI route dưới /internal/api/* (đã chốt Task 6): giao thức S2S
    dùng chung 1 API key bí mật, gửi qua header 'Authorization: Bearer <key>' — khác hẳn
    Bearer token của người dùng (session token ngẫu nhiên lưu DB) dùng ở các route còn lại,
    nhưng dùng chung TÊN header nên phải phân biệt bằng tiền tố đường dẫn.

    Bỏ qua kiểm tra này khi is_dev_env() — quyết định 2026-08-01: giai đoạn demo, đội Server
    Kính chỉ cần gọi thẳng không cần header, ưu tiên tích hợp nhanh hơn bảo mật. PHẢI bật lại
    khi BILLING_ENV=production (is_dev_env() trả False lúc đó)."""
    if not request.path.startswith("/internal/api/"):
        return None
    if is_dev_env():
        return None
    header = request.headers.get("Authorization", "")
    provided = header[len("Bearer "):] if header.startswith("Bearer ") else None
    if not provided or provided != models.INTERNAL_API_KEY:
        return jsonify({"error": "Thiếu hoặc sai Authorization Bearer API key nội bộ."}), 401
    return None


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"})


@app.route("/accounts/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    phone = data.get("phone")
    if not phone:
        return jsonify({"error": "Thiếu số điện thoại."}), 400
    db_path = get_db_path()
    if models.get_account_by_phone(db_path, phone):
        return jsonify({"error": "Số điện thoại đã được đăng ký."}), 409
    try:
        otp = models.generate_otp(db_path, phone, purpose="register")
    except models.OtpCooldownError:
        return jsonify({"error": "Vui lòng đợi trước khi gửi lại mã OTP."}), 429
    response = {"phone": phone, "expires_in": otp["expires_in"]}
    if is_dev_env():
        # TODO: bỏ field này khi có SMS provider thật + BILLING_ENV=production.
        response["otp"] = otp["code"]
    return jsonify(response), 200


@app.route("/accounts/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    phone = data.get("phone")
    if not phone:
        return jsonify({"error": "Thiếu số điện thoại."}), 400
    db_path = get_db_path()
    if not models.get_account_by_phone(db_path, phone):
        return jsonify({"error": "Không tìm thấy tài khoản."}), 404
    try:
        otp = models.generate_otp(db_path, phone, purpose="login")
    except models.OtpCooldownError:
        return jsonify({"error": "Vui lòng đợi trước khi gửi lại mã OTP."}), 429
    response = {"phone": phone, "expires_in": otp["expires_in"]}
    if is_dev_env():
        # TODO: bỏ field này khi có SMS provider thật + BILLING_ENV=production.
        response["otp"] = otp["code"]
    return jsonify(response), 200


@app.route("/accounts/verify-otp", methods=["POST"])
def verify_otp_route():
    data = request.get_json(silent=True) or {}
    phone = data.get("phone")
    code = data.get("code")
    purpose = data.get("purpose")
    if not phone or not code or purpose not in ("register", "login"):
        return jsonify({"error": "Thiếu phone/code hoặc purpose không hợp lệ."}), 400

    db_path = get_db_path()
    try:
        models.verify_otp(db_path, phone, code, purpose)
    except models.OtpNotFoundError:
        return jsonify({"error": "Không tìm thấy yêu cầu OTP, vui lòng gửi lại."}), 404
    except models.OtpExpiredError:
        return jsonify({"error": "Mã OTP đã hết hạn."}), 410
    except models.OtpTooManyAttemptsError:
        return jsonify({"error": "Nhập sai quá số lần cho phép, vui lòng gửi lại mã."}), 429
    except models.OtpInvalidError:
        return jsonify({"error": "Mã OTP không đúng."}), 401

    if purpose == "register":
        try:
            account_id = models.create_account(db_path, phone)
        except ValueError:
            # Trường hợp hiếm: verify lặp lại sau khi account đã được tạo — coi là idempotent.
            account_id = models.get_account_by_phone(db_path, phone)["id"]
        status_code = 201
    else:
        account = models.get_account_by_phone(db_path, phone)
        if not account:
            return jsonify({"error": "Không tìm thấy tài khoản."}), 404
        account_id = account["id"]
        status_code = 200

    token = models.create_session(db_path, account_id)
    return jsonify({"account_id": account_id, "token": token}), status_code


@app.route("/accounts/logout", methods=["POST"])
def logout():
    token = get_bearer_token()
    if not token:
        return jsonify({"error": "Thiếu token."}), 401
    models.revoke_session(get_db_path(), token)
    return jsonify({"message": "Đăng xuất thành công."}), 200


@app.route("/account", methods=["GET"])
def get_my_account_route():
    """Thông tin tài khoản đang đăng nhập — cần cho màn Hồ sơ (Profile) phía app. Trước đây
    KHÔNG có endpoint nào trả về thông tin account (chỉ có account_id trong response
    verify-otp) — gap thật, mới bổ sung 2026-08-02."""
    db_path = get_db_path()
    account_id = models.get_account_id_by_token(db_path, get_bearer_token())
    if account_id is None:
        return jsonify({"error": "Thiếu hoặc sai token xác thực."}), 401
    account = models.get_account_by_id(db_path, account_id)
    account["created_at"] = _display_dt(account.get("created_at"))
    account["is_admin"] = bool(account["is_admin"])
    return jsonify(account), 200


def _require_own_device(db_path, device_id):
    """Trả (device_dict, None) nếu hợp lệ, hoặc (None, (response, status)) nếu lỗi.
    Dùng cho các route thao tác thiết bị từ APP người dùng (khác /status, /consume, /seen
    là các route gọi từ thiết bị/kính, không cần token người dùng)."""
    caller_account_id = models.get_account_id_by_token(db_path, get_bearer_token())
    if caller_account_id is None:
        return None, (jsonify({"error": "Thiếu hoặc sai token xác thực."}), 401)
    device = models.get_device(db_path, device_id)
    if device is None:
        return None, (jsonify({"error": "Không tìm thấy thiết bị."}), 404)
    if device["account_id"] != caller_account_id:
        return None, (jsonify({"error": "Không có quyền thao tác trên thiết bị này."}), 403)
    return device, None


def _verify_action_otp(db_path, account_id, otp_code):
    """Xác thực lại bằng OTP (purpose='device_action') trước hành động nhạy cảm
    (Khoá/Báo mất/Đổi kính — đã chốt cùng người dùng). Trả None nếu hợp lệ,
    hoặc (response, status) nếu lỗi."""
    if not otp_code:
        return jsonify({"error": "Thiếu otp_code."}), 400
    account = models.get_account_by_id(db_path, account_id)
    try:
        models.verify_otp(db_path, account["phone"], otp_code, purpose="device_action")
    except models.OtpNotFoundError:
        return jsonify({"error": "Chưa yêu cầu OTP hoặc đã dùng, vui lòng gửi lại."}), 404
    except models.OtpExpiredError:
        return jsonify({"error": "Mã OTP đã hết hạn."}), 410
    except models.OtpTooManyAttemptsError:
        return jsonify({"error": "Nhập sai quá số lần cho phép, vui lòng gửi lại mã."}), 429
    except models.OtpInvalidError:
        return jsonify({"error": "Mã OTP không đúng."}), 401
    return None


@app.route("/devices/link", methods=["POST"])
def link_device():
    db_path = get_db_path()
    account_id = models.get_account_id_by_token(db_path, get_bearer_token())
    if account_id is None:
        return jsonify({"error": "Thiếu hoặc sai token xác thực."}), 401
    data = request.get_json(silent=True) or {}
    serial_number = data.get("serial_number")
    if not serial_number:
        return jsonify({"error": "Thiếu serial_number."}), 400
    try:
        device_id = models.link_device(db_path, account_id, serial_number)
    except models.SerialNotProvisionedError:
        return jsonify({"error": "Serial không hợp lệ hoặc chưa xuất xưởng."}), 404
    except models.SerialAlreadyLinkedError:
        return jsonify({"error": "Thiết bị đã được liên kết."}), 409
    return jsonify({"device_id": device_id, "serial_number": serial_number, "status": "active"}), 201


@app.route("/devices", methods=["GET"])
def list_devices():
    db_path = get_db_path()
    account_id = models.get_account_id_by_token(db_path, get_bearer_token())
    if account_id is None:
        return jsonify({"error": "Thiếu hoặc sai token xác thực."}), 401
    devices = models.list_devices_for_account(db_path, account_id)
    for device in devices:
        for field in ("last_seen_bluetooth_at", "last_seen_cellular_at", "last_reset_at", "paired_at"):
            device[field] = _display_dt(device.get(field))
    return jsonify(devices), 200


@app.route("/devices/<device_id>", methods=["GET"])
def get_device_info(device_id):
    db_path = get_db_path()
    device, error = _require_own_device(db_path, device_id)
    if error:
        return error
    for field in ("last_seen_bluetooth_at", "last_seen_cellular_at", "last_reset_at", "paired_at"):
        device[field] = _display_dt(device.get(field))
    return jsonify(device), 200


@app.route("/devices/<device_id>/request-action-otp", methods=["POST"])
def request_device_action_otp(device_id):
    db_path = get_db_path()
    device, error = _require_own_device(db_path, device_id)
    if error:
        return error
    account = models.get_account_by_id(db_path, device["account_id"])
    try:
        otp = models.generate_otp(db_path, account["phone"], purpose="device_action")
    except models.OtpCooldownError:
        return jsonify({"error": "Vui lòng đợi trước khi gửi lại mã OTP."}), 429
    response = {"expires_in": otp["expires_in"]}
    if is_dev_env():
        response["otp"] = otp["code"]
    return jsonify(response), 200


@app.route("/devices/<device_id>/lock", methods=["POST"])
def lock_device_route(device_id):
    db_path = get_db_path()
    device, error = _require_own_device(db_path, device_id)
    if error:
        return error
    data = request.get_json(silent=True) or {}
    otp_error = _verify_action_otp(db_path, device["account_id"], data.get("otp_code"))
    if otp_error:
        return otp_error
    try:
        models.lock_device(db_path, device_id)
    except models.InvalidTransitionError:
        return jsonify({"error": "Thiết bị không ở trạng thái có thể khoá."}), 409
    return jsonify({"device_id": device_id, "status": "locked"}), 200


@app.route("/devices/<device_id>/unlock", methods=["POST"])
def unlock_device_route(device_id):
    db_path = get_db_path()
    device, error = _require_own_device(db_path, device_id)
    if error:
        return error
    try:
        models.unlock_device(db_path, device_id)
    except models.InvalidTransitionError:
        return jsonify({"error": "Thiết bị không ở trạng thái có thể mở khoá."}), 409
    return jsonify({"device_id": device_id, "status": "active"}), 200


@app.route("/devices/<device_id>/report-lost", methods=["POST"])
def report_lost_route(device_id):
    db_path = get_db_path()
    device, error = _require_own_device(db_path, device_id)
    if error:
        return error
    data = request.get_json(silent=True) or {}
    otp_error = _verify_action_otp(db_path, device["account_id"], data.get("otp_code"))
    if otp_error:
        return otp_error
    try:
        models.report_lost(db_path, device_id)
    except models.InvalidTransitionError:
        return jsonify({"error": "Thiết bị không ở trạng thái có thể báo mất."}), 409
    return jsonify({"device_id": device_id, "status": "lost"}), 200


@app.route("/devices/<device_id>/recover", methods=["POST"])
def recover_device_route(device_id):
    db_path = get_db_path()
    device, error = _require_own_device(db_path, device_id)
    if error:
        return error
    try:
        models.recover_device(db_path, device_id)
    except models.InvalidTransitionError:
        return jsonify({"error": "Thiết bị không ở trạng thái 'đã mất' để khôi phục."}), 409
    return jsonify({"device_id": device_id, "status": "active"}), 200


@app.route("/devices/<device_id>/reset", methods=["POST"])
def reset_device_route(device_id):
    db_path = get_db_path()
    device, error = _require_own_device(db_path, device_id)
    if error:
        return error
    models.factory_reset_device(db_path, device_id)
    return jsonify({"device_id": device_id, "status": device["status"]}), 200


@app.route("/devices/<device_id>/replace", methods=["POST"])
def replace_device_route(device_id):
    db_path = get_db_path()
    device, error = _require_own_device(db_path, device_id)
    if error:
        return error
    data = request.get_json(silent=True) or {}
    new_serial_number = data.get("new_serial_number")
    if not new_serial_number:
        return jsonify({"error": "Thiếu new_serial_number."}), 400
    otp_error = _verify_action_otp(db_path, device["account_id"], data.get("otp_code"))
    if otp_error:
        return otp_error
    try:
        new_device_id = models.replace_device(db_path, device_id, new_serial_number)
    except models.InvalidTransitionError:
        return jsonify({"error": "Thiết bị đã được đổi trước đó."}), 409
    except models.SerialNotProvisionedError:
        return jsonify({"error": "Serial mới không hợp lệ hoặc chưa xuất xưởng."}), 404
    except models.SerialAlreadyLinkedError:
        return jsonify({"error": "Serial mới đã được liên kết."}), 409
    return jsonify({"device_id": new_device_id, "status": "active"}), 201


@app.route("/devices/<device_id>/seen", methods=["POST"])
def device_seen_route(device_id):
    """Thiết bị/kính tự báo cáo trạng thái kết nối — KHÔNG cần token người dùng
    (device-to-backend, giống /status và /consume). Xem BACKEND_FLOWS.md §2.3."""
    data = request.get_json(silent=True) or {}
    channel = data.get("channel")
    try:
        models.report_device_seen(
            get_db_path(), device_id, channel, data.get("battery"), data.get("firmware")
        )
    except models.DeviceNotFoundError:
        return jsonify({"error": "Không tìm thấy thiết bị."}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"message": "Đã cập nhật trạng thái kết nối thiết bị."}), 200


@app.route("/devices/<device_id>/status", methods=["GET"])
def device_status(device_id):
    db_path = get_db_path()
    status = models.get_device_status(db_path, device_id)
    if status is None:
        return jsonify({"error": "Không tìm thấy thiết bị."}), 404
    return jsonify(status), 200


@app.route("/devices/<device_id>/consume", methods=["POST"])
def consume(device_id):
    db_path = get_db_path()
    try:
        remaining = models.consume_quota(db_path, device_id)
    except models.DeviceNotActiveError:
        return jsonify(
            {"error": "Thiết bị đang bị khoá/báo mất, không thể sử dụng tính năng AI."}
        ), 403
    if remaining is None:
        return jsonify({"error": "Không tìm thấy thiết bị."}), 404
    return jsonify({"quota_remaining": remaining}), 200


@app.route("/packages", methods=["GET"])
def list_packages():
    return jsonify([
        {
            "tier": tier,
            "monthly_price": tiers.get_price(tier, "monthly"),
            "yearly_price": tiers.get_price(tier, "yearly"),
            "quota_limit": info["quota_limit"],
            "allowed_intents": info["allowed_intents"],
        }
        for tier, info in tiers.TIERS.items()
    ]), 200


@app.route("/payment/checkout", methods=["POST"])
def payment_checkout():
    db_path = get_db_path()
    account_id = models.get_account_id_by_token(db_path, get_bearer_token())
    if account_id is None:
        return jsonify({"error": "Thiếu hoặc sai token xác thực."}), 401
    data = request.get_json(silent=True) or {}
    tier = data.get("tier")
    billing_cycle = data.get("billing_cycle")
    discount_code = data.get("discount_code")
    try:
        result = models.create_checkout(db_path, account_id, tier, billing_cycle, discount_code)
    except models.InvalidTierError:
        return jsonify({"error": "Gói không hợp lệ."}), 400
    except models.DiscountCodeInvalidError:
        return jsonify({"error": "Mã giảm giá không hợp lệ hoặc đã hết lượt dùng."}), 400
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(result), 201


@app.route("/payment/webhook", methods=["POST"])
def payment_webhook():
    # Mô phỏng callback cổng thanh toán thật — KHÔNG cần token người dùng (gọi từ gateway).
    # TODO: khi có gateway thật, thêm bước xác minh chữ ký trước khi tin (BACKEND_FLOWS.md §4.1).
    db_path = get_db_path()
    data = request.get_json(silent=True) or {}
    gateway_ref = data.get("gateway_ref")
    status = data.get("status")
    if not gateway_ref or status not in ("paid", "failed"):
        return jsonify({"error": "Thiếu gateway_ref hoặc status không hợp lệ."}), 400
    try:
        result = models.handle_payment_webhook(db_path, gateway_ref, status)
    except models.TransactionNotFoundError:
        return jsonify({"error": "Không tìm thấy giao dịch."}), 404
    return jsonify(result), 200


@app.route("/subscription", methods=["GET"])
def subscription_status():
    db_path = get_db_path()
    account_id = models.get_account_id_by_token(db_path, get_bearer_token())
    if account_id is None:
        return jsonify({"error": "Thiếu hoặc sai token xác thực."}), 401
    status = models.get_subscription_status(db_path, account_id)
    if status is None:
        return jsonify({"error": "Không tìm thấy thuê bao."}), 404
    status["expires_at"] = _display_dt(status.get("expires_at"))
    return jsonify(status), 200


def _require_admin(db_path):
    """Trả (account_id, None) nếu token hợp lệ và account có is_admin=True,
    hoặc (None, (response, status)) nếu không. is_admin là cờ tạm (Task 3b),
    xem models.is_account_admin để biết lý do chưa dùng Roles module thật."""
    account_id = models.get_account_id_by_token(db_path, get_bearer_token())
    if account_id is None:
        return None, (jsonify({"error": "Thiếu hoặc sai token xác thực."}), 401)
    if not models.is_account_admin(db_path, account_id):
        return None, (jsonify({"error": "Chỉ admin mới có quyền thao tác này."}), 403)
    return account_id, None


@app.route("/admin/transactions/<transaction_id>/refund", methods=["POST"])
def refund_transaction_route(transaction_id):
    db_path = get_db_path()
    _, error = _require_admin(db_path)
    if error:
        return error
    try:
        result = models.refund_transaction(db_path, transaction_id)
    except models.TransactionNotFoundError:
        return jsonify({"error": "Không tìm thấy giao dịch."}), 404
    except models.TransactionNotRefundableError:
        return jsonify(
            {
                "error": "Giao dịch không đủ điều kiện hoàn tiền "
                "(chưa thanh toán, đã hoàn tiền, hoặc đã quá hạn refund)."
            }
        ), 409
    return jsonify(result), 200


@app.route("/admin/transactions/stale-pending", methods=["GET"])
def stale_pending_transactions_route():
    db_path = get_db_path()
    _, error = _require_admin(db_path)
    if error:
        return error
    return jsonify(models.find_stale_pending_transactions(db_path)), 200


@app.route("/admin/notifications/failed", methods=["GET"])
def list_failed_notifications_route():
    """Xem các lần báo Server Kính bị lỗi (mất mạng/HTTP lỗi) — chưa có cron tự động,
    dùng route này + /retry để xử lý tay (xem BACKEND_FLOWS §5.1d)."""
    db_path = get_db_path()
    _, error = _require_admin(db_path)
    if error:
        return error
    return jsonify(models.list_failed_notifications(db_path)), 200


@app.route("/admin/notifications/retry-failed", methods=["POST"])
def retry_failed_notifications_route():
    db_path = get_db_path()
    _, error = _require_admin(db_path)
    if error:
        return error
    retried = models.retry_failed_notifications(db_path)
    return jsonify({"retried": retried}), 200


@app.route("/admin/subscriptions/check-expiry", methods=["POST"])
def check_expiry_route():
    """Quét chủ động subscription hết hạn + báo Server Kính/push app (quyết định 2026-08-01,
    xem models.scan_and_notify_expired_subscriptions) — chưa có cron tự động, gọi tay/lên lịch
    ngoài, giống hệt /admin/notifications/retry-failed."""
    db_path = get_db_path()
    _, error = _require_admin(db_path)
    if error:
        return error
    checked = models.scan_and_notify_expired_subscriptions(db_path)
    return jsonify({"checked": checked}), 200


@app.route("/emergency-contacts", methods=["GET"])
def list_emergency_contacts_route():
    db_path = get_db_path()
    account_id = models.get_account_id_by_token(db_path, get_bearer_token())
    if account_id is None:
        return jsonify({"error": "Thiếu hoặc sai token xác thực."}), 401
    return jsonify(models.list_emergency_contacts(db_path, account_id)), 200


@app.route("/emergency-contacts", methods=["POST"])
def add_emergency_contact_route():
    db_path = get_db_path()
    account_id = models.get_account_id_by_token(db_path, get_bearer_token())
    if account_id is None:
        return jsonify({"error": "Thiếu hoặc sai token xác thực."}), 401
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    phone = data.get("phone")
    if not name or not phone:
        return jsonify({"error": "Thiếu name hoặc phone."}), 400
    contact_id = models.add_emergency_contact(
        db_path, account_id, name, phone, is_primary=bool(data.get("is_primary", False))
    )
    return jsonify({"contact_id": contact_id}), 201


@app.route("/emergency-contacts/<contact_id>", methods=["PATCH"])
def update_emergency_contact_route(contact_id):
    db_path = get_db_path()
    account_id = models.get_account_id_by_token(db_path, get_bearer_token())
    if account_id is None:
        return jsonify({"error": "Thiếu hoặc sai token xác thực."}), 401
    data = request.get_json(silent=True) or {}
    try:
        models.update_emergency_contact(
            db_path, account_id, contact_id,
            name=data.get("name"), phone=data.get("phone"), is_primary=data.get("is_primary"),
        )
    except models.EmergencyContactNotFoundError:
        return jsonify({"error": "Không tìm thấy liên hệ."}), 404
    return jsonify({"message": "Đã cập nhật liên hệ khẩn cấp."}), 200


@app.route("/emergency-contacts/<contact_id>", methods=["DELETE"])
def delete_emergency_contact_route(contact_id):
    db_path = get_db_path()
    account_id = models.get_account_id_by_token(db_path, get_bearer_token())
    if account_id is None:
        return jsonify({"error": "Thiếu hoặc sai token xác thực."}), 401
    try:
        models.delete_emergency_contact(db_path, account_id, contact_id)
    except models.EmergencyContactNotFoundError:
        return jsonify({"error": "Không tìm thấy liên hệ."}), 404
    return jsonify({"message": "Đã xoá liên hệ khẩn cấp."}), 200


@app.route("/saved-places", methods=["GET"])
def list_saved_places_route():
    db_path = get_db_path()
    account_id = models.get_account_id_by_token(db_path, get_bearer_token())
    if account_id is None:
        return jsonify({"error": "Thiếu hoặc sai token xác thực."}), 401
    return jsonify(models.list_saved_places(db_path, account_id)), 200


@app.route("/saved-places", methods=["POST"])
def add_saved_place_route():
    """place_type='home' ghi đè bản ghi home cũ nếu có (chỉ giữ 1 nhà/account) — xem
    models.add_saved_place. place_type='other' cần `label` để phân biệt (dùng khi dispatch)."""
    db_path = get_db_path()
    account_id = models.get_account_id_by_token(db_path, get_bearer_token())
    if account_id is None:
        return jsonify({"error": "Thiếu hoặc sai token xác thực."}), 401
    data = request.get_json(silent=True) or {}
    place_type = data.get("place_type")
    lat = data.get("lat")
    lng = data.get("lng")
    if place_type not in models.PLACE_TYPES:
        return jsonify({"error": f"place_type phải là một trong {models.PLACE_TYPES}."}), 400
    if lat is None or lng is None:
        return jsonify({"error": "Thiếu lat/lng."}), 400
    if place_type == "other" and not data.get("label"):
        return jsonify({"error": "Thiếu label cho place_type='other'."}), 400
    place_id = models.add_saved_place(
        db_path, account_id, place_type, lat, lng,
        address=data.get("address"), label=data.get("label"),
    )
    return jsonify({"place_id": place_id}), 201


@app.route("/saved-places/<place_id>", methods=["PATCH"])
def update_saved_place_route(place_id):
    db_path = get_db_path()
    account_id = models.get_account_id_by_token(db_path, get_bearer_token())
    if account_id is None:
        return jsonify({"error": "Thiếu hoặc sai token xác thực."}), 401
    data = request.get_json(silent=True) or {}
    try:
        models.update_saved_place(
            db_path, account_id, place_id,
            label=data.get("label"), lat=data.get("lat"), lng=data.get("lng"),
            address=data.get("address"),
        )
    except models.SavedPlaceNotFoundError:
        return jsonify({"error": "Không tìm thấy địa điểm."}), 404
    return jsonify({"message": "Đã cập nhật địa điểm."}), 200


@app.route("/saved-places/<place_id>", methods=["DELETE"])
def delete_saved_place_route(place_id):
    db_path = get_db_path()
    account_id = models.get_account_id_by_token(db_path, get_bearer_token())
    if account_id is None:
        return jsonify({"error": "Thiếu hoặc sai token xác thực."}), 401
    try:
        models.delete_saved_place(db_path, account_id, place_id)
    except models.SavedPlaceNotFoundError:
        return jsonify({"error": "Không tìm thấy địa điểm."}), 404
    return jsonify({"message": "Đã xoá địa điểm."}), 200


@app.route("/devices/<device_id>/sos/press", methods=["POST"])
def sos_press_route(device_id):
    # SOS bấm từ app điện thoại của chính người dùng -> cần token, khác /location, /seen, /consume
    # vốn là device-to-backend (xem BACKEND_FLOWS.md §5.1).
    db_path = get_db_path()
    _, error = _require_own_device(db_path, device_id)
    if error:
        return error
    result = models.press_sos_button(db_path, device_id)
    return jsonify(result), 200


@app.route("/sos/<location_token>", methods=["GET"])
def sos_public_location_route(location_token):
    # Link công khai, KHÔNG cần đăng nhập (đã chốt Task 4) — người thân bấm từ SMS xem ngay.
    db_path = get_db_path()
    try:
        event = models.get_sos_event_by_token(db_path, location_token)
    except models.SosEventNotFoundError:
        return jsonify({"error": "Không tìm thấy hoặc link đã hết hạn."}), 404
    event["created_at"] = _display_dt(event.get("created_at"))
    return jsonify(event), 200


@app.route("/devices/<device_id>/location", methods=["POST"])
def report_location_route(device_id):
    # Device-to-backend (kính/điện thoại tự báo cáo định kỳ) — không cần token người dùng,
    # giống /seen, /status, /consume.
    data = request.get_json(silent=True) or {}
    lat = data.get("lat")
    lng = data.get("lng")
    if lat is None or lng is None:
        return jsonify({"error": "Thiếu lat/lng."}), 400
    try:
        models.report_location(get_db_path(), device_id, lat, lng)
    except models.DeviceNotFoundError:
        return jsonify({"error": "Không tìm thấy thiết bị."}), 404
    return jsonify({"message": "Đã ghi nhận vị trí."}), 200


@app.route("/location/current", methods=["GET"])
def current_location_route():
    db_path = get_db_path()
    account_id = models.get_account_id_by_token(db_path, get_bearer_token())
    if account_id is None:
        return jsonify({"error": "Thiếu hoặc sai token xác thực."}), 401
    location = models.get_current_location(db_path, account_id)
    if location is None:
        return jsonify({"error": "Chưa có dữ liệu vị trí."}), 404
    location["updated_at"] = _display_dt(location.get("updated_at"))
    return jsonify(location), 200


@app.route("/devices/<device_id>/activity-log", methods=["POST"])
def add_activity_log_route(device_id):
    # Device-to-backend giống /location — thiết bị/app tự gửi title mốc hoạt động (đã chốt
    # Task 4: chưa có auto-detect điểm đến).
    data = request.get_json(silent=True) or {}
    title = data.get("title")
    if not title:
        return jsonify({"error": "Thiếu title."}), 400
    db_path = get_db_path()
    device = models.get_device(db_path, device_id)
    if device is None:
        return jsonify({"error": "Không tìm thấy thiết bị."}), 404
    models.add_activity_log_entry(db_path, device["account_id"], title)
    return jsonify({"message": "Đã ghi nhận hoạt động."}), 200


@app.route("/activity-log", methods=["GET"])
def activity_log_route():
    db_path = get_db_path()
    account_id = models.get_account_id_by_token(db_path, get_bearer_token())
    if account_id is None:
        return jsonify({"error": "Thiếu hoặc sai token xác thực."}), 401
    entries = models.get_activity_log(db_path, account_id)
    for entry in entries:
        entry["recorded_at"] = _display_dt(entry.get("recorded_at"))
    return jsonify(entries), 200


@app.route("/internal/api/v1/sos/trigger", methods=["POST"])
def internal_sos_trigger_route():
    """Điểm tiếp nhận DUY NHẤT cho tín hiệu SOS từ Server Kính — khác hẳn
    /devices/{id}/sos/press (điện thoại người dùng gọi, có Bearer token của người dùng).
    Ở đây Server Kính đã tự đếm đủ 3 lần nhấn, chỉ cần gọi 1 lần kèm vị trí. Xác thực S2S
    đã được middleware `_enforce_internal_api_auth` xử lý chung cho mọi route /internal/api/*."""
    data = request.get_json(silent=True) or {}
    serial_number = data.get("device_id")  # device_id trong hợp đồng S2S = serial_number (đã chốt Task 7)
    location = data.get("location") or {}
    lat = location.get("latitude")
    lng = location.get("longitude")
    if not serial_number or lat is None or lng is None:
        return jsonify({"error": "Thiếu device_id hoặc location.latitude/longitude."}), 400
    try:
        models.trigger_sos_from_device(get_db_path(), serial_number, lat, lng)
    except models.DeviceNotFoundError:
        return jsonify({"error": "Không tìm thấy thiết bị."}), 404
    # 202 Accepted: đã tiếp nhận và xử lý (mock đồng bộ ở giai đoạn này) — Server Kính
    # không cần chờ/quan tâm chi tiết gửi SMS/robo-call/push.
    return jsonify({"status": "accepted"}), 202


@app.route("/devices/<device_id>/push-token", methods=["POST"])
def register_push_token_route(device_id):
    """App điện thoại tự gọi khi khởi động/đăng nhập, cần token người dùng (chủ thiết bị) —
    khác các route device-to-backend còn lại vì đây là app, không phải kính, tự đăng ký.
    Xem SERVER_KINH_PROTOCOL.md mục C.3."""
    db_path = get_db_path()
    device, error = _require_own_device(db_path, device_id)
    if error:
        return error
    data = request.get_json(silent=True) or {}
    platform = data.get("platform")
    push_token = data.get("push_token")
    if platform not in ("android", "ios") or not push_token:
        return jsonify({"error": "Thiếu hoặc sai platform ('android'/'ios') hoặc push_token."}), 400
    models.register_push_token(db_path, device["id"], platform, push_token)
    return jsonify({"message": "Đã đăng ký push token."}), 200


@app.route("/internal/api/v1/actions/dispatch", methods=["POST"])
def internal_actions_dispatch_route():
    """Server Kính gọi khi cần app điện thoại tự thực hiện 1 hành động (gọi khẩn cấp/gọi
    liên hệ/chỉ đường/đặt Grab) — thiết kế đề xuất, SERVER_KINH_PROTOCOL.md mục C.3. Xác thực
    S2S đã được middleware `_enforce_internal_api_auth` xử lý chung."""
    data = request.get_json(silent=True) or {}
    serial_number = data.get("device_id")
    request_id = data.get("request_id")
    action = data.get("action")
    params = data.get("params") or {}
    timestamp_utc = data.get("timestamp_utc")
    if not serial_number or not request_id or not action or not timestamp_utc:
        return jsonify({"error": "Thiếu device_id, request_id, action hoặc timestamp_utc."}), 400
    if action == "call_contact" and not params.get("contact_query"):
        return jsonify({"error": "Thiếu params.contact_query cho action call_contact."}), 400
    if action in ("navigate", "book_grab") and not params.get("place"):
        return jsonify(
            {"error": f'Thiếu params.place (vd. "home") cho action {action}.'}
        ), 400
    try:
        result = models.dispatch_kinh_action(
            get_db_path(), serial_number, request_id, action, params, timestamp_utc
        )
    except models.InvalidKinhActionError:
        return jsonify({"error": "action không hợp lệ."}), 400
    except models.DeviceNotFoundError:
        return jsonify({"error": "Không tìm thấy thiết bị."}), 404
    except models.EmergencyContactNotFoundError:
        return jsonify({"error": "Không tìm thấy liên hệ khẩn cấp phù hợp."}), 404
    except models.SavedPlaceNotFoundError:
        return jsonify({"error": "Không tìm thấy địa điểm đã lưu phù hợp (params.place)."}), 404
    status_code = 200 if result.get("duplicate") or result["status"] != "dispatched" else 202
    return jsonify({"request_id": result["request_id"], "status": result["status"]}), status_code


@app.route("/devices/<device_id>/actions/<request_id>/report", methods=["POST"])
def report_kinh_action_route(device_id, request_id):
    """App điện thoại tự báo kết quả xử lý hành động (đã gọi/không tìm thấy liên hệ/thất bại/
    đang xử lý) — cần token người dùng vì app đã đăng nhập. SERVER_KINH_PROTOCOL.md mục C.3."""
    db_path = get_db_path()
    device, error = _require_own_device(db_path, device_id)
    if error:
        return error
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if status not in models.KINH_ACTION_REPORT_STATUSES:
        return jsonify(
            {"error": f"status phải là một trong {models.KINH_ACTION_REPORT_STATUSES}."}
        ), 400
    try:
        models.report_kinh_action_result(db_path, device["id"], request_id, status, data.get("detail"))
    except models.KinhActionRequestNotFoundError:
        return jsonify({"error": "Không tìm thấy request_id cho thiết bị này."}), 404
    return jsonify({"message": "Đã ghi nhận kết quả."}), 200


@app.route("/devices/<device_id>/pending-actions", methods=["GET"])
def get_pending_kinh_actions_route(device_id):
    """App tự poll định kỳ (quyết định 2026-08-02) để biết có action nào Server Kính vừa
    dispatch mà app chưa xử lý/report — thay push (Expo Go không nhận remote push thật). Cần
    token người dùng, phải là chủ thiết bị — cùng kiểu bảo vệ với /push-token, /actions/.../report."""
    db_path = get_db_path()
    device, error = _require_own_device(db_path, device_id)
    if error:
        return error
    pending = models.get_pending_kinh_actions(db_path, device["id"])
    for item in pending:
        item["created_at"] = _display_dt(item.get("created_at"))
    return jsonify(pending), 200


@app.route("/internal/api/v1/actions/<request_id>/result", methods=["GET"])
def internal_get_action_result_route(request_id):
    """Server Kính poll lại kết quả xử lý 1 action đã dispatch (đã app report chưa, kết quả
    ra sao) để có thể phản hồi người dùng bằng giọng nói qua kính. Xác thực S2S đã được
    middleware `_enforce_internal_api_auth` xử lý chung. SERVER_KINH_PROTOCOL.md mục 3.3."""
    try:
        result = models.get_kinh_action_result(get_db_path(), request_id)
    except models.KinhActionRequestNotFoundError:
        return jsonify({"error": "Không tìm thấy request_id."}), 404
    return jsonify(result), 200


@app.route("/community/groups", methods=["GET"])
def list_community_groups_route():
    return jsonify(models.list_community_groups(get_db_path())), 200


@app.route("/community/groups/<group_id>/join", methods=["POST"])
def join_community_group_route(group_id):
    db_path = get_db_path()
    account_id = models.get_account_id_by_token(db_path, get_bearer_token())
    if account_id is None:
        return jsonify({"error": "Thiếu hoặc sai token xác thực."}), 401
    try:
        models.join_community_group(db_path, account_id, group_id)
    except models.GroupNotFoundError:
        return jsonify({"error": "Không tìm thấy nhóm."}), 404
    return jsonify({"message": "Đã tham gia nhóm."}), 200


@app.route("/community/posts", methods=["GET"])
def list_community_posts_route():
    return jsonify(models.list_community_posts(get_db_path())), 200


@app.route("/community/posts", methods=["POST"])
def add_community_post_route():
    db_path = get_db_path()
    account_id = models.get_account_id_by_token(db_path, get_bearer_token())
    if account_id is None:
        return jsonify({"error": "Thiếu hoặc sai token xác thực."}), 401
    data = request.get_json(silent=True) or {}
    author_name = data.get("author_name")
    title = data.get("title")
    content = data.get("content")
    if not author_name or not title or not content:
        return jsonify({"error": "Thiếu author_name/title/content."}), 400
    post_id = models.add_community_post(db_path, account_id, author_name, title, content)
    return jsonify({"post_id": post_id}), 201


@app.route("/community/events", methods=["GET"])
def list_community_events_route():
    return jsonify(models.list_community_events(get_db_path())), 200


@app.route("/community/events/<event_id>/save", methods=["POST"])
def save_event_route(event_id):
    db_path = get_db_path()
    account_id = models.get_account_id_by_token(db_path, get_bearer_token())
    if account_id is None:
        return jsonify({"error": "Thiếu hoặc sai token xác thực."}), 401
    try:
        models.save_event(db_path, account_id, event_id)
    except models.EventNotFoundError:
        return jsonify({"error": "Không tìm thấy sự kiện."}), 404
    return jsonify({"message": "Đã lưu sự kiện."}), 200


@app.route("/community/events/<event_id>/save", methods=["DELETE"])
def unsave_event_route(event_id):
    db_path = get_db_path()
    account_id = models.get_account_id_by_token(db_path, get_bearer_token())
    if account_id is None:
        return jsonify({"error": "Thiếu hoặc sai token xác thực."}), 401
    models.unsave_event(db_path, account_id, event_id)
    return jsonify({"message": "Đã bỏ lưu sự kiện."}), 200


@app.route("/community/events/saved", methods=["GET"])
def list_saved_events_route():
    db_path = get_db_path()
    account_id = models.get_account_id_by_token(db_path, get_bearer_token())
    if account_id is None:
        return jsonify({"error": "Thiếu hoặc sai token xác thực."}), 401
    return jsonify(models.list_saved_events(db_path, account_id)), 200


@app.route("/support/articles", methods=["GET"])
def list_support_articles_route():
    return jsonify(models.list_support_articles(get_db_path(), request.args.get("kind"))), 200


@app.route("/support/tickets", methods=["POST"])
def create_support_ticket_route():
    db_path = get_db_path()
    account_id = models.get_account_id_by_token(db_path, get_bearer_token())
    if account_id is None:
        return jsonify({"error": "Thiếu hoặc sai token xác thực."}), 401
    data = request.get_json(silent=True) or {}
    category = data.get("category")
    description = data.get("description")
    if not description:
        return jsonify({"error": "Thiếu description."}), 400
    try:
        ticket_id = models.create_support_ticket(db_path, account_id, category, description)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"ticket_id": ticket_id}), 201


@app.route("/support/tickets", methods=["GET"])
def list_own_support_tickets_route():
    db_path = get_db_path()
    account_id = models.get_account_id_by_token(db_path, get_bearer_token())
    if account_id is None:
        return jsonify({"error": "Thiếu hoặc sai token xác thực."}), 401
    return jsonify(models.list_own_support_tickets(db_path, account_id)), 200


@app.route("/support/hotline/call-log", methods=["POST"])
def log_hotline_call_route():
    db_path = get_db_path()
    # Không bắt buộc đăng nhập — account_id chỉ ghi nếu có token hợp lệ (BACKEND_FLOWS §7.3).
    account_id = models.get_account_id_by_token(db_path, get_bearer_token())
    models.log_hotline_call(db_path, account_id)
    return jsonify({"message": "Đã ghi nhận cuộc gọi hotline."}), 200


@app.route("/admin/support/tickets", methods=["GET"])
def list_all_support_tickets_route():
    db_path = get_db_path()
    _, error = _require_admin(db_path)
    if error:
        return error
    return jsonify(models.list_all_support_tickets(db_path, request.args.get("status"))), 200


@app.route("/admin/support/tickets/<ticket_id>/status", methods=["PATCH"])
def update_support_ticket_status_route(ticket_id):
    db_path = get_db_path()
    _, error = _require_admin(db_path)
    if error:
        return error
    data = request.get_json(silent=True) or {}
    try:
        models.update_support_ticket_status(db_path, ticket_id, data.get("status"))
    except models.TicketNotFoundError:
        return jsonify({"error": "Không tìm thấy ticket."}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"message": "Đã cập nhật trạng thái ticket."}), 200


if __name__ == "__main__":
    get_db_path()
    port = int(os.environ.get("PORT", 5005))
    app.run(host="0.0.0.0", port=port)
