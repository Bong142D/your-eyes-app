import json
import logging
import math
import os
import secrets
import sqlite3
import uuid
from datetime import datetime, timedelta

import requests

from tiers import DEFAULT_TIER, TIERS, get_price

logger = logging.getLogger(__name__)

SCHEMA_PATH = __file__.replace("models.py", "schema.sql")

# Giao thức Server-to-Server (S2S) với Server Kính (đã chốt Task 6): 1 API key bí mật DÙNG CHUNG
# cho cả 2 chiều — Server Kính gọi ta kèm header này, và ta cũng dùng chính key này khi gọi họ.
INTERNAL_API_KEY = os.environ.get("INTERNAL_API_KEY", "dev-internal-key")

# GIẢ ĐỊNH chưa xác nhận với đội Server Kính: "Server Kính" = ocr-server-service trong
# docker-compose.yml (port 5004). Đổi qua ENV nếu địa chỉ thật khác.
GLASSES_SERVER_BASE_URL = os.environ.get("GLASSES_SERVER_BASE_URL", "http://localhost:5004")
GLASSES_SERVER_TIMEOUT_SECONDS = int(os.environ.get("GLASSES_SERVER_TIMEOUT_SECONDS", 5))

# Twilio (SMS/voice) — quyết định 2026-08-02: gửi OTP + SOS (SMS + robo-call) qua Twilio nếu
# đã cấu hình đủ 3 biến ENV dưới, tự động fallback về mock/log (hành vi cũ, SIMULATING_SMS/
# SIMULATING_ROBO_CALL) nếu chưa có tài khoản — không cần sửa code khi có tài khoản thật, chỉ
# cần điền ENV. Gửi thất bại KHÔNG được làm hỏng luồng chính (OTP/SOS vẫn tạo/trigger thành
# công dù SMS lỗi) — xem _send_sms/_make_robocall.
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_FROM_NUMBER = os.environ.get("TWILIO_FROM_NUMBER")
TWILIO_DEFAULT_COUNTRY_CODE = os.environ.get("TWILIO_DEFAULT_COUNTRY_CODE", "+84")


def _twilio_configured():
    return bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_FROM_NUMBER)


def _to_e164(phone):
    """Đổi SĐT lưu dạng nội địa ('0912345678') sang E.164 Twilio yêu cầu ('+84912345678').
    Giữ nguyên nếu đã là E.164 (bắt đầu bằng '+')."""
    if phone.startswith("+"):
        return phone
    if phone.startswith("0"):
        return TWILIO_DEFAULT_COUNTRY_CODE + phone[1:]
    return phone


def _send_sms(to_phone, message):
    """Gửi SMS thật qua Twilio nếu đã cấu hình, tự fallback log mock nếu chưa. KHÔNG raise —
    lỗi gửi SMS không được làm hỏng luồng gọi (OTP/SOS). Trả True nếu gửi thật thành công."""
    if not _twilio_configured():
        logger.info(f"SIMULATING_SMS to {to_phone}: {message}")
        return False
    try:
        from twilio.rest import Client
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        client.messages.create(body=message, from_=TWILIO_FROM_NUMBER, to=_to_e164(to_phone))
        logger.info(f"TWILIO_SMS_SENT to {to_phone}")
        return True
    except Exception as e:
        logger.error(f"TWILIO_SMS_FAILED to {to_phone}: {e}")
        return False


def _make_robocall(to_phone, message):
    """Gọi thoại thật qua Twilio (TwiML <Say> gửi kèm trực tiếp, không cần webhook URL riêng)
    nếu đã cấu hình, tự fallback log mock nếu chưa. KHÔNG raise."""
    if not _twilio_configured():
        logger.info(f"SIMULATING_ROBO_CALL to {to_phone}")
        return False
    try:
        from twilio.rest import Client
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        twiml = f'<Response><Say language="vi-VN">{message}</Say></Response>'
        client.calls.create(to=_to_e164(to_phone), from_=TWILIO_FROM_NUMBER, twiml=twiml)
        logger.info(f"TWILIO_ROBOCALL_SENT to {to_phone}")
        return True
    except Exception as e:
        logger.error(f"TWILIO_ROBOCALL_FAILED to {to_phone}: {e}")
        return False

# Placeholder defaults — chưa chốt số liệu chính thức (xem BACKEND_FLOWS.md §1.1 "❓ Cần chốt").
# Có thể chỉnh qua biến môi trường mà không cần sửa code.
OTP_LENGTH = 6
OTP_TTL_SECONDS = int(os.environ.get("OTP_TTL_SECONDS", 300))  # 5 phút
OTP_MAX_ATTEMPTS = int(os.environ.get("OTP_MAX_ATTEMPTS", 5))
OTP_RESEND_COOLDOWN_SECONDS = int(os.environ.get("OTP_RESEND_COOLDOWN_SECONDS", 60))
SESSION_TTL_SECONDS = int(os.environ.get("SESSION_TTL_SECONDS", 30 * 24 * 3600))  # 30 ngày

# Đã chốt cùng người dùng (Task 3): ngưỡng "sắp hết hạn" = 7 ngày; quá hạn thì hạ về
# free NGAY (tính toán khi đọc, không cần job nền); đổi gói giữa kỳ = chu kỳ mới hoàn toàn
# (không cộng dồn ngày còn lại của gói cũ).
SUBSCRIPTION_EXPIRING_SOON_DAYS = int(os.environ.get("SUBSCRIPTION_EXPIRING_SOON_DAYS", 7))
BILLING_CYCLE_DAYS = {"monthly": 30, "yearly": 365}

# Placeholder defaults — chưa chốt số liệu chính thức (xem BACKEND_FLOWS.md §5.1/5.2 "❓ Cần chốt").
# Kiến trúc (mock SMS/push, link công khai, ghi vị trí liên tục, activity log ghi thủ công) ĐÃ
# chốt cùng người dùng ở Task 4 — chỉ các con số dưới đây là tạm, có thể chỉnh qua ENV.
SOS_PRESS_THRESHOLD = int(os.environ.get("SOS_PRESS_THRESHOLD", 3))
SOS_PRESS_WINDOW_SECONDS = int(os.environ.get("SOS_PRESS_WINDOW_SECONDS", 10))
LOCATION_LINK_TTL_HOURS = int(os.environ.get("LOCATION_LINK_TTL_HOURS", 24))
LOCATION_LOG_RETENTION_DAYS = int(os.environ.get("LOCATION_LOG_RETENTION_DAYS", 30))
LOCATION_MOVING_THRESHOLD_METERS = int(os.environ.get("LOCATION_MOVING_THRESHOLD_METERS", 20))

# Mục C, SERVER_KINH_PROTOCOL.md — Server Kính yêu cầu app điện thoại tự thực hiện hành động.
# Thiết kế đề xuất, chưa chốt 100%: đặt Grab dùng deep-link mở app Grab có sẵn (KHÔNG dùng
# Grab Partner API thật — chưa có hợp đồng đối tác); push gửi cho app hiện chỉ log giả lập
# (SIMULATING_PUSH_ACTION), chưa nối Firebase/APNs thật, giống cách SMS SOS đang mock.
KINH_ACTIONS = ("call_emergency_contact", "call_contact", "navigate", "book_grab")
KINH_ACTION_REPORT_STATUSES = ("done", "no_match", "failed", "in_progress", "cancelled")

# Địa điểm đã lưu (quyết định 2026-08-03): navigate/book_grab CHỈ nhận địa điểm đã lưu sẵn
# trong app qua params.place (vd. "home"), KHÔNG còn nhận toạ độ tự do từ Server Kính nữa —
# để tránh rủi ro AI/STT nhận nhầm địa chỉ rồi tự đặt xe/tự chỉ đường tới nơi sai. Chọn 1 địa
# điểm MỚI (chưa lưu sẵn) là tính năng để mở rộng sau, chưa làm ở giai đoạn này.
PLACE_TYPES = ("home", "other")


class OtpError(Exception):
    """Base class cho các lỗi liên quan tới OTP."""


class OtpCooldownError(OtpError):
    pass


class OtpNotFoundError(OtpError):
    pass


class OtpExpiredError(OtpError):
    pass


class OtpTooManyAttemptsError(OtpError):
    pass


class OtpInvalidError(OtpError):
    pass


class DeviceError(Exception):
    """Base class cho các lỗi liên quan tới thiết bị."""


class SerialNotProvisionedError(DeviceError):
    """Serial không có trong device_catalog (chưa xuất xưởng / không hợp lệ)."""


class SerialAlreadyLinkedError(DeviceError):
    """Serial đã được pairing với 1 device khác."""


class DeviceNotFoundError(DeviceError):
    pass


class InvalidTransitionError(DeviceError):
    """Thao tác không hợp lệ với trạng thái hiện tại của thiết bị (vd. khoá thiết bị đã lost)."""


class DeviceNotActiveError(DeviceError):
    """Thiết bị đang locked/lost/replaced nên không được dùng tính năng AI."""


class PaymentError(Exception):
    """Base class cho các lỗi liên quan tới thanh toán/subscription."""


class InvalidTierError(PaymentError):
    pass


class DiscountCodeInvalidError(PaymentError):
    """Mã giảm giá không tồn tại, đã hết hạn, hoặc đã dùng hết lượt."""


class TransactionNotFoundError(PaymentError):
    pass


class TransactionNotRefundableError(PaymentError):
    """Giao dịch chưa thanh toán, đã hoàn tiền trước đó, hoặc đã quá thời hạn refund."""


class SafetyError(Exception):
    """Base class cho các lỗi liên quan tới SOS/Safety."""


class EmergencyContactNotFoundError(SafetyError):
    pass


class SosEventNotFoundError(SafetyError):
    """Không tìm thấy sos_event theo location_token, hoặc link đã hết hạn (cố tình không phân
    biệt 2 trường hợp để tránh dò token bằng cách thử nhiều lần)."""


class SavedPlaceNotFoundError(SafetyError):
    """Không tìm thấy địa điểm đã lưu (id không thuộc account, hoặc chưa từng set 'home')."""


class KinhActionError(Exception):
    """Base class cho lỗi liên quan tới hành động Server Kính yêu cầu app điện thoại thực hiện
    (SERVER_KINH_PROTOCOL.md mục C — gọi khẩn cấp/gọi liên hệ/chỉ đường/đặt Grab)."""


class InvalidKinhActionError(KinhActionError):
    pass


class KinhActionRequestNotFoundError(KinhActionError):
    pass


class CommunityError(Exception):
    """Base class cho các lỗi liên quan tới Community Module."""


class GroupNotFoundError(CommunityError):
    pass


class EventNotFoundError(CommunityError):
    pass


class SupportError(Exception):
    """Base class cho các lỗi liên quan tới Support Module."""


class TicketNotFoundError(SupportError):
    pass


SUPPORT_TICKET_CATEGORIES = ("bug_report", "support_request")
SUPPORT_TICKET_STATUSES = ("open", "in_progress", "resolved")


# Đã chốt cùng người dùng (Task 3b): refund trong vòng 7 ngày sau khi thanh toán;
# đối soát coi giao dịch "pending" quá 30 phút là bất thường (nghi ngờ lỡ webhook).
REFUND_WINDOW_DAYS = int(os.environ.get("REFUND_WINDOW_DAYS", 7))
STALE_PENDING_MINUTES = int(os.environ.get("STALE_PENDING_MINUTES", 30))


def _connect(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path):
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = f.read()
    conn = _connect(db_path)
    try:
        conn.executescript(schema)
        conn.commit()
    finally:
        conn.close()


def create_account(db_path, phone):
    conn = _connect(db_path)
    try:
        existing = conn.execute(
            "SELECT id FROM account WHERE phone = ?", (phone,)
        ).fetchone()
        if existing:
            raise ValueError("phone already registered")
        account_id = uuid.uuid4().hex
        now = datetime.utcnow().isoformat()
        conn.execute(
            "INSERT INTO account (id, phone, created_at) VALUES (?, ?, ?)",
            (account_id, phone, now),
        )
        expires_at = (datetime.utcnow() + timedelta(days=30)).isoformat()
        conn.execute(
            "INSERT INTO subscription (account_id, tier, expires_at) VALUES (?, ?, ?)",
            (account_id, DEFAULT_TIER, expires_at),
        )
        conn.commit()
        return account_id
    finally:
        conn.close()


def get_account_by_phone(db_path, phone):
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT id, phone FROM account WHERE phone = ?", (phone,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_account_by_id(db_path, account_id):
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT id, phone, created_at, is_admin FROM account WHERE id = ?", (account_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def is_account_admin(db_path, account_id):
    """Cờ is_admin đơn giản (Task 3b) — placeholder tạm thời cho tới khi có Roles module
    thật (mục 1.7), dùng để gate các endpoint /admin/*."""
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT is_admin FROM account WHERE id = ?", (account_id,)
        ).fetchone()
        return bool(row and row["is_admin"])
    finally:
        conn.close()


def set_is_admin(db_path, account_id, is_admin=True):
    conn = _connect(db_path)
    try:
        conn.execute(
            "UPDATE account SET is_admin = ? WHERE id = ?",
            (1 if is_admin else 0, account_id),
        )
        conn.commit()
    finally:
        conn.close()


def generate_otp(db_path, phone, purpose):
    """Tạo (hoặc thay thế) mã OTP đang chờ cho phone+purpose. Trả về {"code", "expires_in"}."""
    conn = _connect(db_path)
    try:
        now = datetime.utcnow()
        existing = conn.execute(
            "SELECT created_at FROM otp_request WHERE phone = ? AND purpose = ?",
            (phone, purpose),
        ).fetchone()
        if existing:
            last_created = datetime.fromisoformat(existing["created_at"])
            if now - last_created < timedelta(seconds=OTP_RESEND_COOLDOWN_SECONDS):
                raise OtpCooldownError()
        code = f"{secrets.randbelow(10 ** OTP_LENGTH):0{OTP_LENGTH}d}"
        expires_at = (now + timedelta(seconds=OTP_TTL_SECONDS)).isoformat()
        conn.execute(
            "INSERT INTO otp_request (phone, purpose, code, attempts, created_at, expires_at, consumed_at) "
            "VALUES (?, ?, ?, 0, ?, ?, NULL) "
            "ON CONFLICT(phone, purpose) DO UPDATE SET "
            "code=excluded.code, attempts=0, created_at=excluded.created_at, "
            "expires_at=excluded.expires_at, consumed_at=NULL",
            (phone, purpose, code, now.isoformat(), expires_at),
        )
        conn.commit()
    finally:
        conn.close()
    # Gửi SMS SAU khi đã commit — lỗi gửi SMS không được làm hỏng việc tạo OTP đã thành công
    # (cùng nguyên tắc với notify_glasses_subscription_status). Twilio thật nếu đã cấu hình ENV,
    # tự fallback mock/log nếu chưa (quyết định 2026-08-02, xem _send_sms).
    minutes = OTP_TTL_SECONDS // 60
    _send_sms(phone, f"Mã OTP Your Eyes của bạn là: {code}. Hết hạn sau {minutes} phút. Không chia sẻ mã này cho ai.")
    return {"code": code, "expires_in": OTP_TTL_SECONDS}


def verify_otp(db_path, phone, code, purpose):
    """Xác thực OTP. Raise 1 trong các OtpError con nếu không hợp lệ, trả True nếu đúng."""
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT code, attempts, expires_at, consumed_at FROM otp_request "
            "WHERE phone = ? AND purpose = ?",
            (phone, purpose),
        ).fetchone()
        if not row or row["consumed_at"]:
            raise OtpNotFoundError()
        now = datetime.utcnow()
        if datetime.fromisoformat(row["expires_at"]) < now:
            raise OtpExpiredError()
        if row["attempts"] >= OTP_MAX_ATTEMPTS:
            raise OtpTooManyAttemptsError()
        if row["code"] != code:
            conn.execute(
                "UPDATE otp_request SET attempts = attempts + 1 WHERE phone = ? AND purpose = ?",
                (phone, purpose),
            )
            conn.commit()
            raise OtpInvalidError()
        conn.execute(
            "UPDATE otp_request SET consumed_at = ? WHERE phone = ? AND purpose = ?",
            (now.isoformat(), phone, purpose),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def create_session(db_path, account_id):
    conn = _connect(db_path)
    try:
        token = secrets.token_urlsafe(32)
        now = datetime.utcnow()
        expires_at = (now + timedelta(seconds=SESSION_TTL_SECONDS)).isoformat()
        conn.execute(
            "INSERT INTO session (token, account_id, created_at, expires_at, revoked_at) "
            "VALUES (?, ?, ?, ?, NULL)",
            (token, account_id, now.isoformat(), expires_at),
        )
        conn.commit()
        return token
    finally:
        conn.close()


def get_account_id_by_token(db_path, token):
    if not token:
        return None
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT account_id, expires_at, revoked_at FROM session WHERE token = ?",
            (token,),
        ).fetchone()
        if not row or row["revoked_at"]:
            return None
        if datetime.fromisoformat(row["expires_at"]) < datetime.utcnow():
            return None
        return row["account_id"]
    finally:
        conn.close()


def revoke_session(db_path, token):
    conn = _connect(db_path)
    try:
        conn.execute(
            "UPDATE session SET revoked_at = ? WHERE token = ?",
            (datetime.utcnow().isoformat(), token),
        )
        conn.commit()
    finally:
        conn.close()


def add_catalog_serial(db_path, serial_number):
    """Nạp 1 serial 'đã xuất xưởng' vào catalog (mô phỏng nhà sản xuất cung cấp)."""
    conn = _connect(db_path)
    try:
        conn.execute(
            "INSERT OR IGNORE INTO device_catalog (serial_number, provisioned_at) VALUES (?, ?)",
            (serial_number, datetime.utcnow().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def link_device(db_path, account_id, serial_number):
    """Pairing thiết bị mới theo serial_number (BACKEND_FLOWS.md §2.1)."""
    conn = _connect(db_path)
    try:
        if not conn.execute(
            "SELECT 1 FROM device_catalog WHERE serial_number = ?", (serial_number,)
        ).fetchone():
            raise SerialNotProvisionedError()
        if conn.execute(
            "SELECT 1 FROM device WHERE serial_number = ?", (serial_number,)
        ).fetchone():
            raise SerialAlreadyLinkedError()
        device_id = uuid.uuid4().hex
        now = datetime.utcnow().isoformat()
        conn.execute(
            "INSERT INTO device (id, account_id, serial_number, status, battery, firmware, "
            "last_seen_bluetooth_at, last_seen_cellular_at, last_reset_at, paired_at) "
            "VALUES (?, ?, ?, 'active', NULL, NULL, NULL, NULL, NULL, ?)",
            (device_id, account_id, serial_number, now),
        )
        conn.commit()
    finally:
        conn.close()
    # Báo Server Kính SAU khi đã commit — lỗi mạng không được chặn việc pairing đã thành công
    # (đã chốt Task 7, xem notify_glasses_link_status).
    notify_glasses_link_status(db_path, serial_number, "linked")
    return device_id


def get_device(db_path, device_id):
    """Thông tin thiết bị đầy đủ cho màn Quản lý thiết bị (khác với get_device_status - dùng cho AI gateway)."""
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT id, account_id, serial_number, status, battery, firmware, "
            "last_seen_bluetooth_at, last_seen_cellular_at, last_reset_at, paired_at "
            "FROM device WHERE id = ?",
            (device_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_devices_for_account(db_path, account_id):
    """Danh sách thiết bị đã liên kết với account, mới liên kết trước — cho màn Quản lý thiết bị
    khi app chưa biết device_id nào để gọi GET /devices/{id}."""
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT id, account_id, serial_number, status, battery, firmware, "
            "last_seen_bluetooth_at, last_seen_cellular_at, last_reset_at, paired_at "
            "FROM device WHERE account_id = ? ORDER BY paired_at DESC",
            (account_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def _set_device_status(conn, device_id, allowed_from, new_status):
    row = conn.execute("SELECT status FROM device WHERE id = ?", (device_id,)).fetchone()
    if not row:
        raise DeviceNotFoundError()
    if allowed_from is not None and row["status"] not in allowed_from:
        raise InvalidTransitionError()
    conn.execute("UPDATE device SET status = ? WHERE id = ?", (new_status, device_id))


def lock_device(db_path, device_id):
    conn = _connect(db_path)
    try:
        _set_device_status(conn, device_id, allowed_from=["active"], new_status="locked")
        conn.commit()
    finally:
        conn.close()


def unlock_device(db_path, device_id):
    conn = _connect(db_path)
    try:
        _set_device_status(conn, device_id, allowed_from=["locked"], new_status="active")
        conn.commit()
    finally:
        conn.close()


def report_lost(db_path, device_id):
    conn = _connect(db_path)
    try:
        _set_device_status(conn, device_id, allowed_from=["active", "locked"], new_status="lost")
        conn.commit()
    finally:
        conn.close()


def recover_device(db_path, device_id):
    """Tìm lại thiết bị đã báo mất — không cần OTP (chỉ Khoá/Báo mất/Đổi kính mới cần)."""
    conn = _connect(db_path)
    try:
        _set_device_status(conn, device_id, allowed_from=["lost"], new_status="active")
        conn.commit()
    finally:
        conn.close()


def factory_reset_device(db_path, device_id):
    """Khôi phục cấu hình — KHÔNG đổi status/serial (khác Đổi kính). Backend hiện chưa lưu
    'cấu hình cá nhân' nào khác ngoài status, nên chỉ ghi nhận thời điểm reset (last_reset_at)."""
    conn = _connect(db_path)
    try:
        row = conn.execute("SELECT status FROM device WHERE id = ?", (device_id,)).fetchone()
        if not row:
            raise DeviceNotFoundError()
        conn.execute(
            "UPDATE device SET last_reset_at = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), device_id),
        )
        conn.commit()
    finally:
        conn.close()


def replace_device(db_path, device_id, new_serial_number):
    """Đổi kính: đóng vĩnh viễn device cũ (status=replaced), pairing serial mới cho cùng account."""
    conn = _connect(db_path)
    try:
        old = conn.execute(
            "SELECT account_id, status, serial_number FROM device WHERE id = ?", (device_id,)
        ).fetchone()
        if not old:
            raise DeviceNotFoundError()
        if old["status"] == "replaced":
            raise InvalidTransitionError()
        if not conn.execute(
            "SELECT 1 FROM device_catalog WHERE serial_number = ?", (new_serial_number,)
        ).fetchone():
            raise SerialNotProvisionedError()
        if conn.execute(
            "SELECT 1 FROM device WHERE serial_number = ?", (new_serial_number,)
        ).fetchone():
            raise SerialAlreadyLinkedError()

        conn.execute("UPDATE device SET status = 'replaced' WHERE id = ?", (device_id,))
        new_device_id = uuid.uuid4().hex
        now = datetime.utcnow().isoformat()
        conn.execute(
            "INSERT INTO device (id, account_id, serial_number, status, battery, firmware, "
            "last_seen_bluetooth_at, last_seen_cellular_at, last_reset_at, paired_at) "
            "VALUES (?, ?, ?, 'active', NULL, NULL, NULL, NULL, NULL, ?)",
            (new_device_id, old["account_id"], new_serial_number, now),
        )
        conn.commit()
        old_serial_number = old["serial_number"]
    finally:
        conn.close()
    # Báo Server Kính: serial cũ huỷ liên kết, serial mới được liên kết (đã chốt Task 7).
    notify_glasses_link_status(db_path, old_serial_number, "unlinked")
    notify_glasses_link_status(db_path, new_serial_number, "linked")
    return new_device_id


def report_device_seen(db_path, device_id, channel, battery=None, firmware=None):
    """Cập nhật last_seen theo kênh kết nối ('bluetooth' hoặc 'cellular') + pin/firmware nếu có
    (BACKEND_FLOWS.md §2.3 — 2 kênh kết nối độc lập)."""
    if channel not in ("bluetooth", "cellular"):
        raise ValueError("channel phải là 'bluetooth' hoặc 'cellular'")
    column = "last_seen_bluetooth_at" if channel == "bluetooth" else "last_seen_cellular_at"
    conn = _connect(db_path)
    try:
        row = conn.execute("SELECT id FROM device WHERE id = ?", (device_id,)).fetchone()
        if not row:
            raise DeviceNotFoundError()
        now = datetime.utcnow().isoformat()
        updates = [f"{column} = ?"]
        params = [now]
        if battery is not None:
            updates.append("battery = ?")
            params.append(battery)
        if firmware is not None:
            updates.append("firmware = ?")
            params.append(firmware)
        params.append(device_id)
        conn.execute(f"UPDATE device SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
    finally:
        conn.close()


def _today_period():
    return datetime.utcnow().strftime("%Y-%m-%d")


def _effective_tier(tier, expires_at_iso):
    """Tier THẬT SỰ áp dụng cho quota AI — hạ về free ngay khi hết hạn (đã chốt Task 3),
    dùng chung cho get_device_status/consume_quota để tránh lệch với get_subscription_status."""
    if not expires_at_iso or expires_at_iso <= datetime.utcnow().isoformat():
        return DEFAULT_TIER
    return tier


def _check_and_flag_expiry(conn, account_id, tier, expires_at_iso):
    """Đã chốt Task 7 (thay cho ❓ 'chưa xử lý hết hạn tự nhiên'): KHÔNG có cron — biến 'lazy
    expiry' thành 1 sự kiện DUY NHẤT bằng cờ subscription.expiry_notified_at. Bất kỳ lần đọc
    nào sau khi hết hạn (get_subscription_status hoặc get_device_status — lần nào xảy ra
    trước) đều có thể là điểm phát hiện đầu tiên. Trả về tier đã mua nếu đây là lần đầu phát
    hiện (để caller notify Server Kính status='expired'), None nếu chưa hết hạn/đã báo rồi."""
    if not expires_at_iso or expires_at_iso >= datetime.utcnow().isoformat():
        return None
    row = conn.execute(
        "SELECT expiry_notified_at FROM subscription WHERE account_id = ?", (account_id,)
    ).fetchone()
    if not row or row["expiry_notified_at"]:
        return None
    conn.execute(
        "UPDATE subscription SET expiry_notified_at = ? WHERE account_id = ?",
        (datetime.utcnow().isoformat(), account_id),
    )
    conn.commit()
    return tier


def get_active_device_ids_for_account(db_path, account_id):
    """Trả về device.id nội bộ (khác get_active_device_serials_for_account trả serial_number)
    — dùng để tra device_push_token, vì bảng đó khoá theo device.id nội bộ (xem
    register_push_token / POST /devices/{id}/push-token)."""
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT id FROM device WHERE account_id = ? AND status = 'active'",
            (account_id,),
        ).fetchall()
        return [r["id"] for r in rows]
    finally:
        conn.close()


def _push_subscription_expired_to_app(db_path, account_id, previous_tier, new_tier, expires_at_iso):
    """Push (mock, cùng kiểu dispatch_kinh_action) báo app biết gói vừa hết hạn để tự cập nhật
    UI — quyết định 2026-08-01, thay cho chỉ lazy-detect âm thầm như trước. Gửi tới mọi device
    đang active của account đã đăng ký push token; im lặng (không lỗi) nếu chưa có token nào,
    giống 'no_push_token' ở Phần 3 CONTRACT_SERVER_KINH.md."""
    device_ids = get_active_device_ids_for_account(db_path, account_id)
    if not device_ids:
        return
    conn = _connect(db_path)
    try:
        for device_id in device_ids:
            push_row = conn.execute(
                "SELECT push_token FROM device_push_token WHERE device_id = ?", (device_id,)
            ).fetchone()
            if push_row:
                logger.info(
                    f"SIMULATING_PUSH_SUBSCRIPTION_EXPIRED to device {device_id}: "
                    f"previous_tier={previous_tier} new_tier={new_tier} expires_at={expires_at_iso}"
                )
    finally:
        conn.close()


def _notify_expiry_all_channels(db_path, account_id, expired_tier, expired_cycle, expires_at_iso):
    """Điểm gộp DUY NHẤT khi 1 subscription vừa được phát hiện hết hạn lần đầu (đã qua
    _check_and_flag_expiry hoặc claim trong scan_and_notify_expired_subscriptions) — báo cả
    Server Kính (S2S, mỗi device serial, giữ nguyên hành vi cũ) và app (push, quyết định
    2026-08-01, mới thêm). Dùng chung cho cả đường lazy (get_device_status/
    get_subscription_status) lẫn đường quét chủ động, để không bao giờ thiếu 1 kênh dù đường
    nào phát hiện trước."""
    for serial in get_active_device_serials_for_account(db_path, account_id):
        notify_glasses_subscription_status(
            db_path, serial, plan_id=_plan_id(expired_tier, expired_cycle),
            status="expired", expires_at=expires_at_iso,
        )
    _push_subscription_expired_to_app(db_path, account_id, expired_tier, DEFAULT_TIER, expires_at_iso)


def scan_and_notify_expired_subscriptions(db_path):
    """Quét CHỦ ĐỘNG toàn bộ subscription đã hết hạn nhưng chưa từng báo — quyết định
    2026-08-01 (trước đó chỉ lazy-detect khi có ai gọi /subscription hoặc /status). Dùng chung
    cờ expiry_notified_at với đường lazy, claim từng dòng bằng UPDATE...WHERE...IS NULL +
    kiểm tra rowcount để không báo trùng nếu đường lazy phát hiện trước trong lúc quét đang
    chạy. KHÔNG chạy scheduler trong process (tránh gọi trùng nếu sau này tăng số gunicorn
    worker, và tránh thêm dependency mới) — gọi tay hoặc lên lịch ngoài (cron/Task Scheduler)
    qua POST /admin/subscriptions/check-expiry, giống hệt pattern retry_failed_notifications
    (Task 7). Trả về số subscription vừa được xử lý ở lần gọi này."""
    now_iso = datetime.utcnow().isoformat()
    conn = _connect(db_path)
    try:
        candidates = conn.execute(
            "SELECT account_id, tier, billing_cycle, expires_at FROM subscription "
            "WHERE expires_at < ? AND expiry_notified_at IS NULL",
            (now_iso,),
        ).fetchall()
        claimed = []
        for row in candidates:
            cur = conn.execute(
                "UPDATE subscription SET expiry_notified_at = ? "
                "WHERE account_id = ? AND expiry_notified_at IS NULL",
                (now_iso, row["account_id"]),
            )
            if cur.rowcount:
                claimed.append(dict(row))
        conn.commit()
    finally:
        conn.close()

    for row in claimed:
        _notify_expiry_all_channels(
            db_path, row["account_id"], row["tier"], row["billing_cycle"], row["expires_at"]
        )
    return len(claimed)


def get_device_status(db_path, device_id):
    """Trạng thái dùng cho AI gateway (quota/tier) — gọi bởi thiết bị/kính, không cần token người dùng."""
    conn = _connect(db_path)
    try:
        device = conn.execute(
            "SELECT account_id, status FROM device WHERE id = ?", (device_id,)
        ).fetchone()
        if not device:
            return None
        account_id = device["account_id"]
        sub = conn.execute(
            "SELECT tier, billing_cycle, expires_at FROM subscription WHERE account_id = ?",
            (account_id,),
        ).fetchone()
        now = datetime.utcnow().isoformat()
        subscription_valid = bool(sub) and sub["expires_at"] > now
        tier = _effective_tier(sub["tier"], sub["expires_at"]) if sub else DEFAULT_TIER
        expired_tier, expired_cycle = None, None
        if sub:
            expired_tier = _check_and_flag_expiry(conn, account_id, sub["tier"], sub["expires_at"])
            expired_cycle = sub["billing_cycle"]
        period = _today_period()
        quota_row = conn.execute(
            "SELECT used, limit_value FROM quota WHERE account_id = ? AND period = ?",
            (account_id, period),
        ).fetchone()
        tier_info = TIERS.get(tier, TIERS[DEFAULT_TIER])
        if quota_row:
            remaining = max(0, quota_row["limit_value"] - quota_row["used"])
        else:
            remaining = tier_info["quota_limit"]
        result = {
            "tier": tier,
            "subscription_valid": subscription_valid,
            "quota_remaining": remaining,
            "allowed_intents": tier_info["allowed_intents"],
            "device_status": device["status"],
        }
    finally:
        conn.close()

    if expired_tier:
        _notify_expiry_all_channels(db_path, account_id, expired_tier, expired_cycle, sub["expires_at"])
    return result


def consume_quota(db_path, device_id):
    """Trừ quota cho 1 lần dùng AI. Raise DeviceNotActiveError nếu thiết bị đang
    locked/lost/replaced (BACKEND_FLOWS.md §2.2 — khoá thiết bị thì chặn tính năng AI)."""
    conn = _connect(db_path)
    try:
        device = conn.execute(
            "SELECT account_id, status FROM device WHERE id = ?", (device_id,)
        ).fetchone()
        if not device:
            return None
        if device["status"] != "active":
            raise DeviceNotActiveError()
        account_id = device["account_id"]
        sub = conn.execute(
            "SELECT tier, expires_at FROM subscription WHERE account_id = ?", (account_id,)
        ).fetchone()
        tier = _effective_tier(sub["tier"], sub["expires_at"]) if sub else DEFAULT_TIER
        tier_limit = TIERS.get(tier, TIERS[DEFAULT_TIER])["quota_limit"]
        period = _today_period()
        row = conn.execute(
            "SELECT used, limit_value FROM quota WHERE account_id = ? AND period = ?",
            (account_id, period),
        ).fetchone()
        if row:
            used = row["used"] + 1
            limit_value = row["limit_value"]
            conn.execute(
                "UPDATE quota SET used = ? WHERE account_id = ? AND period = ?",
                (used, account_id, period),
            )
        else:
            used = 1
            limit_value = tier_limit
            conn.execute(
                "INSERT INTO quota (account_id, period, used, limit_value) VALUES (?, ?, ?, ?)",
                (account_id, period, used, limit_value),
            )
        conn.commit()
        return max(0, limit_value - used)
    finally:
        conn.close()


def add_discount_code(db_path, code, percent_off, expires_at=None, max_uses=None):
    conn = _connect(db_path)
    try:
        conn.execute(
            "INSERT OR IGNORE INTO discount_code (code, percent_off, expires_at, max_uses, used_count) "
            "VALUES (?, ?, ?, ?, 0)",
            (code, percent_off, expires_at, max_uses),
        )
        conn.commit()
    finally:
        conn.close()


def _apply_discount(conn, amount, discount_code):
    """Trả (final_amount, code_đã_áp_dụng_hoặc_None). Raise DiscountCodeInvalidError nếu mã sai/hết hạn/hết lượt."""
    if not discount_code:
        return amount, None
    row = conn.execute(
        "SELECT percent_off, expires_at, max_uses, used_count FROM discount_code WHERE code = ?",
        (discount_code,),
    ).fetchone()
    if not row:
        raise DiscountCodeInvalidError()
    if row["expires_at"] and row["expires_at"] < datetime.utcnow().isoformat():
        raise DiscountCodeInvalidError()
    if row["max_uses"] is not None and row["used_count"] >= row["max_uses"]:
        raise DiscountCodeInvalidError()
    final_amount = round(amount * (100 - row["percent_off"]) / 100)
    return final_amount, discount_code


def create_checkout(db_path, account_id, tier, billing_cycle, discount_code=None):
    """Tạo payment_transaction(status=pending) + gateway_ref giả lập (BACKEND_FLOWS.md §4.1).
    Chưa cập nhật subscription — chỉ handle_payment_webhook mới cập nhật khi có 'paid'."""
    if tier not in TIERS:
        raise InvalidTierError()
    if billing_cycle not in BILLING_CYCLE_DAYS:
        raise ValueError("billing_cycle phải là 'monthly' hoặc 'yearly'")
    base_amount = get_price(tier, billing_cycle)
    conn = _connect(db_path)
    try:
        amount, applied_code = _apply_discount(conn, base_amount, discount_code)
        transaction_id = uuid.uuid4().hex
        gateway_ref = f"MOCKPAY-{uuid.uuid4().hex[:16]}"
        now = datetime.utcnow().isoformat()
        conn.execute(
            "INSERT INTO payment_transaction (id, account_id, tier, billing_cycle, amount, "
            "discount_code, status, gateway_ref, created_at, paid_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?, NULL)",
            (transaction_id, account_id, tier, billing_cycle, amount, applied_code, gateway_ref, now),
        )
        conn.commit()
        return {"transaction_id": transaction_id, "amount": amount, "gateway_ref": gateway_ref}
    finally:
        conn.close()


def handle_payment_webhook(db_path, gateway_ref, status):
    """Mô phỏng callback cổng thanh toán. Idempotent: nếu transaction không còn 'pending'
    (đã xử lý trước đó) thì trả kết quả cũ, không xử lý lại lần 2 (BACKEND_FLOWS.md §4.1)."""
    if status not in ("paid", "failed"):
        raise ValueError("status phải là 'paid' hoặc 'failed'")
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT id, account_id, tier, billing_cycle, discount_code, status "
            "FROM payment_transaction WHERE gateway_ref = ?",
            (gateway_ref,),
        ).fetchone()
        if not row:
            raise TransactionNotFoundError()
        if row["status"] != "pending":
            return {"transaction_id": row["id"], "status": row["status"], "already_processed": True}

        now_iso = datetime.utcnow().isoformat()
        conn.execute(
            "UPDATE payment_transaction SET status = ?, paid_at = ? WHERE id = ?",
            (status, now_iso if status == "paid" else None, row["id"]),
        )

        new_expires_at = None
        if status == "paid":
            if row["discount_code"]:
                conn.execute(
                    "UPDATE discount_code SET used_count = used_count + 1 WHERE code = ?",
                    (row["discount_code"],),
                )
            # Đã chốt: đổi/gia hạn gói luôn bắt đầu chu kỳ MỚI hoàn toàn, không cộng dồn
            # ngày còn lại của gói cũ (kể cả khi upgrade giữa kỳ).
            days = BILLING_CYCLE_DAYS[row["billing_cycle"]]
            new_expires_at = (datetime.utcnow() + timedelta(days=days)).isoformat()
            # expiry_notified_at=NULL: reset cờ hết hạn cũ (nếu có) — gói mới có hạn mới,
            # cần cho phép báo Server Kính 'expired' lại khi tới lượt hết hạn tiếp theo.
            conn.execute(
                "INSERT INTO subscription (account_id, tier, billing_cycle, expires_at, "
                "expiry_notified_at) VALUES (?, ?, ?, ?, NULL) "
                "ON CONFLICT(account_id) DO UPDATE SET tier=excluded.tier, "
                "billing_cycle=excluded.billing_cycle, expires_at=excluded.expires_at, "
                "expiry_notified_at=NULL",
                (row["account_id"], row["tier"], row["billing_cycle"], new_expires_at),
            )
        conn.commit()
        account_id, tier, billing_cycle = row["account_id"], row["tier"], row["billing_cycle"]
    finally:
        conn.close()

    if status == "paid":
        # Báo Server Kính SAU khi đã commit subscription — lỗi mạng không được làm hỏng
        # việc thanh toán đã ghi nhận thành công (đã chốt Task 6, xem notify_glasses_subscription_status).
        for serial in get_active_device_serials_for_account(db_path, account_id):
            notify_glasses_subscription_status(
                db_path, serial, plan_id=_plan_id(tier, billing_cycle),
                status="active", expires_at=new_expires_at,
            )
    return {"transaction_id": row["id"], "status": status, "already_processed": False}


def get_subscription_status(db_path, account_id):
    """Trạng thái thuê bao hiển thị cho app: tier hiệu lực + active/expiring_soon/expired.
    Ngưỡng expiring_soon = SUBSCRIPTION_EXPIRING_SOON_DAYS (đã chốt = 7 ngày, xem BACKEND_FLOWS §3.3)."""
    conn = _connect(db_path)
    try:
        sub = conn.execute(
            "SELECT tier, billing_cycle, expires_at FROM subscription WHERE account_id = ?",
            (account_id,),
        ).fetchone()
        if not sub:
            return None
        now = datetime.utcnow()
        expires_at = datetime.fromisoformat(sub["expires_at"])
        if expires_at < now:
            computed_status = "expired"
        elif expires_at - now <= timedelta(days=SUBSCRIPTION_EXPIRING_SOON_DAYS):
            computed_status = "expiring_soon"
        else:
            computed_status = "active"
        effective_tier = _effective_tier(sub["tier"], sub["expires_at"])
        expired_tier = _check_and_flag_expiry(conn, account_id, sub["tier"], sub["expires_at"])
        result = {
            "tier": effective_tier,
            "purchased_tier": sub["tier"],
            "expires_at": sub["expires_at"],
            "status": computed_status,
        }
    finally:
        conn.close()

    if expired_tier:
        _notify_expiry_all_channels(
            db_path, account_id, expired_tier, sub["billing_cycle"], sub["expires_at"]
        )
    return result


def refund_transaction(db_path, transaction_id):
    """Hoàn tiền 1 giao dịch đã 'paid', trong vòng REFUND_WINDOW_DAYS kể từ paid_at.
    Hạ subscription liên quan về free NGAY LẬP TỨC (đã chốt Task 3b) — không chờ hết hạn tự nhiên."""
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT account_id, status, paid_at FROM payment_transaction WHERE id = ?",
            (transaction_id,),
        ).fetchone()
        if not row:
            raise TransactionNotFoundError()
        if row["status"] != "paid" or not row["paid_at"]:
            raise TransactionNotRefundableError()
        paid_at = datetime.fromisoformat(row["paid_at"])
        if datetime.utcnow() - paid_at > timedelta(days=REFUND_WINDOW_DAYS):
            raise TransactionNotRefundableError()

        conn.execute(
            "UPDATE payment_transaction SET status = 'refunded' WHERE id = ?",
            (transaction_id,),
        )
        now_iso = datetime.utcnow().isoformat()
        # expiry_notified_at = now_iso luôn: tránh get_device_status/get_subscription_status
        # tự phát hiện "expired" lần nữa ngay sau đây và gửi trùng thông báo với "cancelled".
        conn.execute(
            "UPDATE subscription SET tier = ?, expires_at = ?, expiry_notified_at = ? "
            "WHERE account_id = ?",
            (DEFAULT_TIER, now_iso, now_iso, row["account_id"]),
        )
        conn.commit()
        account_id = row["account_id"]
    finally:
        conn.close()

    # Gọi Server Kính SAU khi đã commit thay đổi ở DB của ta — lỗi mạng/HTTP không được
    # làm hỏng việc refund đã ghi nhận thành công (đã chốt Task 6).
    for serial in get_active_device_serials_for_account(db_path, account_id):
        notify_glasses_subscription_status(
            db_path, serial, plan_id=_plan_id(DEFAULT_TIER, "monthly"),
            status="cancelled", expires_at=now_iso,
        )
    return {"transaction_id": transaction_id, "status": "refunded"}


# ---------------------------------------------------------------------------
# Giao tiếp Server-to-Server với Server Kính (BACKEND_FLOWS.md §5.1d) — đã chốt Task 6:
# 1 API key bí mật dùng chung 2 chiều, gửi qua "Authorization: Bearer <key>".
# ---------------------------------------------------------------------------

def _plan_id(tier, billing_cycle):
    # ❓ Chưa xác nhận với đội Server Kính: cần báo họ format này ("pro_monthly", "free_monthly"...).
    return f"{tier}_{billing_cycle}"


def get_active_device_serials_for_account(db_path, account_id):
    """Trả về serial_number (KHÔNG phải device.id nội bộ) — đã chốt Task 7: mọi giao tiếp
    S2S dùng serial_number làm device_id, vì đó là định danh Server Kính biết."""
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT serial_number FROM device WHERE account_id = ? AND status = 'active'",
            (account_id,),
        ).fetchall()
        return [r["serial_number"] for r in rows]
    finally:
        conn.close()


# API do Server Kính cung cấp (để billing-service gọi) — endpoint tương ứng từng "kind"
# outbound_notification (đã chốt Task 7, xem BACKEND_FLOWS §5.1d).
_GLASSES_SERVER_ENDPOINTS = {
    "subscription_status": "/internal/api/v1/devices/subscription-status",
    "link_status": "/internal/api/v1/devices/link-status",
}


def _format_dt_for_glasses(value):
    """Format datetime gửi cho Server Kính dạng gọn 'YYYY-MM-DD HH:MM:SS' (quyết định
    2026-08-01, thay ISO thô có microseconds) — khác tầng lưu trữ nội bộ (vẫn giữ ISO)."""
    if not value:
        return value
    try:
        return datetime.fromisoformat(value).strftime("%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return value


def notify_glasses_subscription_status(db_path, serial_number, plan_id, status, expires_at):
    """Báo Server Kính đổi trạng thái thuê bao của 1 thiết bị (device_id = serial_number).
    Ghi vào outbound_notification TRƯỚC khi gọi mạng — lỗi mạng/HTTP không mất bản ghi, có thể
    retry_failed_notifications() sau (đã chốt: không có cron tự động, phải gọi tay/lên lịch riêng)."""
    payload = {
        "device_id": serial_number,
        "subscription": {
            "plan_id": plan_id, "status": status,
            "expires_at": _format_dt_for_glasses(expires_at),
        },
    }
    return _queue_and_send_notification(db_path, "subscription_status", serial_number, payload)


def notify_glasses_link_status(db_path, serial_number, status):
    """Báo Server Kính khi thiết bị được liên kết/huỷ liên kết với tài khoản (khác
    subscription-status). status: 'linked' hoặc 'unlinked' (đã chốt Task 7)."""
    payload = {
        "device_id": serial_number,
        "link_status": {
            "status": status,
            "changed_at": _format_dt_for_glasses(datetime.utcnow().isoformat()),
        },
    }
    return _queue_and_send_notification(db_path, "link_status", serial_number, payload)


def _queue_and_send_notification(db_path, kind, serial_number, payload):
    notification_id = uuid.uuid4().hex
    conn = _connect(db_path)
    try:
        conn.execute(
            "INSERT INTO outbound_notification (id, kind, device_id, payload, status, "
            "attempts, created_at) VALUES (?, ?, ?, ?, 'pending', 0, ?)",
            (notification_id, kind, serial_number, json.dumps(payload),
             datetime.utcnow().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()
    _attempt_send_notification(db_path, notification_id)
    return notification_id


def _attempt_send_notification(db_path, notification_id):
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT kind, payload FROM outbound_notification WHERE id = ?", (notification_id,)
        ).fetchone()
        if not row:
            return
        kind = row["kind"]
        payload = json.loads(row["payload"])
    finally:
        conn.close()

    path = _GLASSES_SERVER_ENDPOINTS.get(kind, _GLASSES_SERVER_ENDPOINTS["subscription_status"])
    url = f"{GLASSES_SERVER_BASE_URL}{path}"
    headers = {
        "Authorization": f"Bearer {INTERNAL_API_KEY}",
        "Content-Type": "application/json",
    }
    conn = _connect(db_path)
    try:
        try:
            resp = requests.post(
                url, json=payload, headers=headers, timeout=GLASSES_SERVER_TIMEOUT_SECONDS
            )
            if not (200 <= resp.status_code < 300):
                raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")
            conn.execute(
                "UPDATE outbound_notification SET status='sent', attempts=attempts+1, "
                "sent_at=? WHERE id=?",
                (datetime.utcnow().isoformat(), notification_id),
            )
            logger.info(
                f"NOTIFIED glasses server: {kind} for device {payload['device_id']} "
                f"-> {resp.status_code}"
            )
        except Exception as exc:  # lỗi mạng (Timeout/ConnectionError) hoặc HTTP lỗi ở trên
            conn.execute(
                "UPDATE outbound_notification SET status='failed', attempts=attempts+1, "
                "last_error=? WHERE id=?",
                (str(exc), notification_id),
            )
            logger.error(
                f"FAILED to notify glasses server ({kind}) for device {payload['device_id']}: {exc}"
            )
        conn.commit()
    finally:
        conn.close()


def list_failed_notifications(db_path):
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT id, device_id, payload, attempts, last_error, created_at "
            "FROM outbound_notification WHERE status = 'failed' ORDER BY created_at ASC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def retry_failed_notifications(db_path):
    """Thử gửi lại toàn bộ outbound_notification đang 'failed' — gọi tay qua endpoint admin,
    CHƯA có cron tự động (nhất quán với find_stale_pending_transactions ở Task 3b)."""
    conn = _connect(db_path)
    try:
        ids = [
            r["id"] for r in conn.execute(
                "SELECT id FROM outbound_notification WHERE status = 'failed'"
            ).fetchall()
        ]
    finally:
        conn.close()
    for notification_id in ids:
        _attempt_send_notification(db_path, notification_id)
    return len(ids)


def find_stale_pending_transactions(db_path, older_than_minutes=None):
    """Đối soát thu hẹp (Task 3b): liệt kê giao dịch 'pending' quá lâu — nghi ngờ lỡ webhook,
    vì chưa có báo cáo từ cổng thanh toán thật để đối chiếu 2 chiều đầy đủ (xem BACKEND_FLOWS §4.3)."""
    minutes = older_than_minutes if older_than_minutes is not None else STALE_PENDING_MINUTES
    cutoff = (datetime.utcnow() - timedelta(minutes=minutes)).isoformat()
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT id, account_id, tier, billing_cycle, amount, gateway_ref, created_at "
            "FROM payment_transaction WHERE status = 'pending' AND created_at < ? "
            "ORDER BY created_at ASC",
            (cutoff,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Emergency Contacts (BACKEND_FLOWS.md §5.1) — chưa có API nào quản lý trước Task 4,
# dù Profile và màn AN TOÀN đều cần danh sách này.
# ---------------------------------------------------------------------------

def _unset_other_primary_contacts(conn, account_id, keep_contact_id):
    """Chỉ 1 liên hệ được là primary tại 1 thời điểm (đã chốt Task 5) — bỏ primary của
    các liên hệ khác trong cùng account khi có 1 liên hệ mới được đánh dấu primary."""
    conn.execute(
        "UPDATE emergency_contact SET is_primary = 0 WHERE account_id = ? AND id != ?",
        (account_id, keep_contact_id),
    )


def add_emergency_contact(db_path, account_id, name, phone, is_primary=False):
    conn = _connect(db_path)
    try:
        contact_id = uuid.uuid4().hex
        conn.execute(
            "INSERT INTO emergency_contact (id, account_id, name, phone, is_primary, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (contact_id, account_id, name, phone, 1 if is_primary else 0,
             datetime.utcnow().isoformat()),
        )
        if is_primary:
            _unset_other_primary_contacts(conn, account_id, contact_id)
        conn.commit()
        return contact_id
    finally:
        conn.close()


def update_emergency_contact(db_path, account_id, contact_id, name=None, phone=None, is_primary=None):
    """Sửa liên hệ khẩn cấp — dùng để đánh dấu primary sau khi đã tạo (đã chốt Task 5:
    field is_primary khi tạo/sửa, không cần endpoint riêng)."""
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT id FROM emergency_contact WHERE id = ? AND account_id = ?",
            (contact_id, account_id),
        ).fetchone()
        if not row:
            raise EmergencyContactNotFoundError()
        updates, params = [], []
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if phone is not None:
            updates.append("phone = ?")
            params.append(phone)
        if is_primary is not None:
            updates.append("is_primary = ?")
            params.append(1 if is_primary else 0)
        if updates:
            params.append(contact_id)
            conn.execute(
                f"UPDATE emergency_contact SET {', '.join(updates)} WHERE id = ?", params
            )
        if is_primary:
            _unset_other_primary_contacts(conn, account_id, contact_id)
        conn.commit()
    finally:
        conn.close()


def list_emergency_contacts(db_path, account_id):
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT id, name, phone, is_primary FROM emergency_contact WHERE account_id = ? "
            "ORDER BY created_at ASC",
            (account_id,),
        ).fetchall()
        return [{**dict(r), "is_primary": bool(r["is_primary"])} for r in rows]
    finally:
        conn.close()


def delete_emergency_contact(db_path, account_id, contact_id):
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT id FROM emergency_contact WHERE id = ? AND account_id = ?",
            (contact_id, account_id),
        ).fetchone()
        if not row:
            raise EmergencyContactNotFoundError()
        conn.execute("DELETE FROM emergency_contact WHERE id = ?", (contact_id,))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Địa điểm đã lưu (quyết định 2026-08-03) — dùng cho navigate/book_grab, xem PLACE_TYPES.
# ---------------------------------------------------------------------------

def add_saved_place(db_path, account_id, place_type, lat, lng, address=None, label=None):
    """place_type='home': chỉ giữ 1 bản ghi/account, tạo mới sẽ THAY THẾ bản ghi home cũ
    (giống cách device_push_token chỉ giữ 1 token/device). place_type='other': cho phép nhiều,
    phân biệt bằng `label` — dispatch_kinh_action tra theo label khi params.place != 'home'."""
    conn = _connect(db_path)
    try:
        if place_type == "home":
            conn.execute(
                "DELETE FROM saved_place WHERE account_id = ? AND place_type = 'home'",
                (account_id,),
            )
        place_id = uuid.uuid4().hex
        conn.execute(
            "INSERT INTO saved_place (id, account_id, place_type, label, lat, lng, address, "
            "created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (place_id, account_id, place_type, label, lat, lng, address,
             datetime.utcnow().isoformat()),
        )
        conn.commit()
        return place_id
    finally:
        conn.close()


def list_saved_places(db_path, account_id):
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT id, place_type, label, lat, lng, address FROM saved_place "
            "WHERE account_id = ? ORDER BY created_at ASC",
            (account_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_saved_place(db_path, account_id, place_id, label=None, lat=None, lng=None, address=None):
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT id FROM saved_place WHERE id = ? AND account_id = ?", (place_id, account_id)
        ).fetchone()
        if not row:
            raise SavedPlaceNotFoundError()
        updates, params = [], []
        if label is not None:
            updates.append("label = ?")
            params.append(label)
        if lat is not None:
            updates.append("lat = ?")
            params.append(lat)
        if lng is not None:
            updates.append("lng = ?")
            params.append(lng)
        if address is not None:
            updates.append("address = ?")
            params.append(address)
        if updates:
            params.append(place_id)
            conn.execute(f"UPDATE saved_place SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
    finally:
        conn.close()


def delete_saved_place(db_path, account_id, place_id):
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT id FROM saved_place WHERE id = ? AND account_id = ?", (place_id, account_id)
        ).fetchone()
        if not row:
            raise SavedPlaceNotFoundError()
        conn.execute("DELETE FROM saved_place WHERE id = ?", (place_id,))
        conn.commit()
    finally:
        conn.close()


def _get_saved_place_for_dispatch(conn, account_id, place_key):
    """`place_key == 'home'` -> tra theo place_type; giá trị khác -> tra theo `label` (không
    phân biệt hoa/thường) trong nhóm 'other'. Dùng bởi dispatch_kinh_action cho navigate/
    book_grab — trả None nếu không tìm thấy (caller tự raise SavedPlaceNotFoundError)."""
    if place_key == "home":
        return conn.execute(
            "SELECT lat, lng, address FROM saved_place WHERE account_id = ? AND place_type = 'home'",
            (account_id,),
        ).fetchone()
    return conn.execute(
        "SELECT lat, lng, address FROM saved_place WHERE account_id = ? AND place_type = 'other' "
        "AND LOWER(label) = LOWER(?)",
        (account_id, place_key or ""),
    ).fetchone()


# ---------------------------------------------------------------------------
# SOS (BACKEND_FLOWS.md §5.1)
# ---------------------------------------------------------------------------

def press_sos_button(db_path, device_id):
    """Ghi 1 lần nhấn nút SOS. Nếu đủ SOS_PRESS_THRESHOLD lần trong SOS_PRESS_WINDOW_SECONDS
    (đã chốt kiến trúc, số liệu là placeholder) thì kích hoạt sos_event: gửi thông báo (mock —
    xem quyết định Task 4) song song tới TẤT CẢ emergency_contact, và ghi 1 dòng activity_log."""
    conn = _connect(db_path)
    try:
        device = conn.execute(
            "SELECT account_id FROM device WHERE id = ?", (device_id,)
        ).fetchone()
        if not device:
            raise DeviceNotFoundError()
        account_id = device["account_id"]
        now = datetime.utcnow()

        conn.execute(
            "INSERT INTO sos_press (device_id, pressed_at) VALUES (?, ?)",
            (device_id, now.isoformat()),
        )
        cutoff = (now - timedelta(seconds=SOS_PRESS_WINDOW_SECONDS)).isoformat()
        press_count = conn.execute(
            "SELECT COUNT(*) AS c FROM sos_press WHERE device_id = ? AND pressed_at >= ?",
            (device_id, cutoff),
        ).fetchone()["c"]

        if press_count < SOS_PRESS_THRESHOLD:
            conn.commit()
            return {"press_count": press_count, "triggered": False}

        # Đủ số lần trong cửa sổ thời gian -> xoá lịch sử nhấn để lần sau đếm lại từ đầu.
        conn.execute("DELETE FROM sos_press WHERE device_id = ?", (device_id,))

        latest = conn.execute(
            "SELECT lat, lng FROM location_log WHERE account_id = ? "
            "ORDER BY recorded_at DESC LIMIT 1",
            (account_id,),
        ).fetchone()
        lat = latest["lat"] if latest else None
        lng = latest["lng"] if latest else None

        event_id = uuid.uuid4().hex
        location_token = secrets.token_urlsafe(24)
        conn.execute(
            "INSERT INTO sos_event (id, account_id, device_id, status, lat, lng, "
            "location_token, created_at) VALUES (?, ?, ?, 'triggered', ?, ?, ?, ?)",
            (event_id, account_id, device_id, lat, lng, location_token, now.isoformat()),
        )

        if lat is not None and lng is not None:
            maps_link = f"http://maps.google.com/maps?q={lat},{lng}"
            sms_content = f"[SOS] {account_id} needs help! Location: {maps_link}"
        else:
            sms_content = f"[SOS] {account_id} needs help! (Chưa có dữ liệu vị trí)"

        contacts = conn.execute(
            "SELECT name, phone FROM emergency_contact WHERE account_id = ?", (account_id,)
        ).fetchall()
        deliveries = []
        for contact in contacts:
            # Gửi SONG SONG tới tất cả liên hệ, cả 2 kênh SMS + push (đã chốt §5.1). SMS qua
            # Twilio thật nếu đã cấu hình ENV, fallback mock/log nếu chưa (quyết định
            # 2026-08-02, xem _send_sms) — push vẫn mock, chưa chọn provider (Firebase/APNs).
            sent_ok = _send_sms(contact["phone"], sms_content)
            sms_status = "sent" if (sent_ok or not _twilio_configured()) else "failed"
            conn.execute(
                "INSERT INTO sos_delivery (id, sos_event_id, contact_phone, channel, "
                "status, sent_at) VALUES (?, ?, ?, 'sms', ?, ?)",
                (uuid.uuid4().hex, event_id, contact["phone"], sms_status, now.isoformat()),
            )
            deliveries.append(
                {"contact_name": contact["name"], "phone": contact["phone"],
                 "channel": "sms", "status": sms_status}
            )
            logger.info(f"SIMULATING_PUSH to {contact['phone']}")
            conn.execute(
                "INSERT INTO sos_delivery (id, sos_event_id, contact_phone, channel, "
                "status, sent_at) VALUES (?, ?, ?, 'push', 'sent', ?)",
                (uuid.uuid4().hex, event_id, contact["phone"], now.isoformat()),
            )
            deliveries.append(
                {"contact_name": contact["name"], "phone": contact["phone"],
                 "channel": "push", "status": "sent"}
            )

        conn.execute(
            "INSERT INTO activity_log_entry (id, account_id, title, recorded_at) "
            "VALUES (?, ?, ?, ?)",
            (uuid.uuid4().hex, account_id, "Đã gửi tín hiệu SOS", now.isoformat()),
        )
        conn.commit()
        return {
            "press_count": press_count,
            "triggered": True,
            "sos_event_id": event_id,
            "location_token": location_token,
            "deliveries": deliveries,
        }
    finally:
        conn.close()


def trigger_sos_from_device(db_path, serial_number, lat, lng):
    """SOS kích hoạt bởi Server Kính — khác `press_sos_button` (backend tự đếm 3 lần nhấn
    do điện thoại gọi trực tiếp): ở đây Server Kính đã tự đếm đủ 3 lần và chỉ gọi 1 lần duy
    nhất kèm sẵn vị trí (không cần đọc location_log). `device_id` trong payload S2S = serial_number
    (đã chốt Task 7) — tra ngược ra device.id nội bộ để dùng thống nhất trong sos_event.
    Dùng chung sos_event/sos_delivery/activity_log_entry với luồng cũ. Gửi SMS + push tới
    TẤT CẢ liên hệ, robo-call CHỈ tới liên hệ is_primary=True (đã chốt Task 5)."""
    conn = _connect(db_path)
    try:
        device = conn.execute(
            "SELECT id, account_id FROM device WHERE serial_number = ?", (serial_number,)
        ).fetchone()
        if not device:
            raise DeviceNotFoundError()
        device_id = device["id"]
        account_id = device["account_id"]
        now = datetime.utcnow()
        logger.info(f"SOS TRIGGERED for device {serial_number} at location ({lat}, {lng})")

        event_id = uuid.uuid4().hex
        location_token = secrets.token_urlsafe(24)
        conn.execute(
            "INSERT INTO sos_event (id, account_id, device_id, status, lat, lng, "
            "location_token, created_at) VALUES (?, ?, ?, 'triggered', ?, ?, ?, ?)",
            (event_id, account_id, device_id, lat, lng, location_token, now.isoformat()),
        )

        contacts = conn.execute(
            "SELECT name, phone, is_primary FROM emergency_contact WHERE account_id = ?",
            (account_id,),
        ).fetchall()

        maps_link = f"http://maps.google.com/maps?q={lat},{lng}"
        deliveries = []
        primary_contact = None
        for contact in contacts:
            sms_content = f"[SOS] {account_id} needs help! Location: {maps_link}"
            # Twilio thật nếu đã cấu hình ENV, tự fallback mock/log nếu chưa (quyết định
            # 2026-08-02, xem _send_sms). status phản ánh đúng kết quả gửi thật khi có Twilio —
            # trước đây luôn hardcode "sent" vì mock luôn "thành công". Mock (chưa cấu hình
            # Twilio) vẫn giữ "sent" để không đổi hành vi test/demo hiện tại.
            sent_ok = _send_sms(contact["phone"], sms_content)
            sms_status = "sent" if (sent_ok or not _twilio_configured()) else "failed"
            conn.execute(
                "INSERT INTO sos_delivery (id, sos_event_id, contact_phone, channel, "
                "status, sent_at) VALUES (?, ?, ?, 'sms', ?, ?)",
                (uuid.uuid4().hex, event_id, contact["phone"], sms_status, now.isoformat()),
            )
            deliveries.append(
                {"contact_name": contact["name"], "phone": contact["phone"],
                 "channel": "sms", "status": sms_status}
            )

            logger.info(
                f"PUSH_NOTIFICATION_SENT: yêu cầu gọi điện tới {contact['name']} ({contact['phone']})"
            )
            conn.execute(
                "INSERT INTO sos_delivery (id, sos_event_id, contact_phone, channel, "
                "status, sent_at) VALUES (?, ?, ?, 'push', 'sent', ?)",
                (uuid.uuid4().hex, event_id, contact["phone"], now.isoformat()),
            )
            deliveries.append(
                {"contact_name": contact["name"], "phone": contact["phone"],
                 "channel": "push", "status": "sent"}
            )

            if contact["is_primary"]:
                primary_contact = contact

        if primary_contact:
            robocall_message = f"Cảnh báo khẩn cấp Your Eyes. {primary_contact['name']} cần giúp đỡ. Vui lòng kiểm tra tin nhắn để xem vị trí."
            call_ok = _make_robocall(primary_contact["phone"], robocall_message)
            robocall_status = "sent" if (call_ok or not _twilio_configured()) else "failed"
            conn.execute(
                "INSERT INTO sos_delivery (id, sos_event_id, contact_phone, channel, "
                "status, sent_at) VALUES (?, ?, ?, 'robocall', ?, ?)",
                (uuid.uuid4().hex, event_id, primary_contact["phone"], robocall_status, now.isoformat()),
            )
            deliveries.append(
                {"contact_name": primary_contact["name"], "phone": primary_contact["phone"],
                 "channel": "robocall", "status": robocall_status}
            )
        else:
            logger.info("No primary emergency contact set — skipping robo-call.")

        conn.execute(
            "INSERT INTO activity_log_entry (id, account_id, title, recorded_at) "
            "VALUES (?, ?, ?, ?)",
            (uuid.uuid4().hex, account_id, "Đã gửi tín hiệu SOS", now.isoformat()),
        )
        conn.commit()
        result = {
            "sos_event_id": event_id,
            "location_token": location_token,
            "deliveries": deliveries,
            "primary_contact_notified": primary_contact is not None,
        }
    finally:
        conn.close()

    # Dispatch 1 kinh_action_request "call_emergency_contact" cho CHÍNH thiết bị vừa trigger SOS
    # (khác nhóm sos_delivery gửi cho CONTACTS ở trên) — quyết định 2026-08-02: app tự poll
    # GET /devices/{id}/pending-actions (Expo Go không nhận được push thật, xem BACKEND_FLOWS.md
    # §5.1) và tự hiện màn hình cảnh báo toàn màn hình + xác nhận gọi liên hệ chính. Tái dùng
    # nguyên vẹn dispatch_kinh_action (tự tra is_primary, ghi kinh_action_request, không tạo
    # khái niệm mới) — gọi SAU khi đã commit SOS, lỗi ở bước này (vd. thiếu primary contact,
    # dù đã check ở trên — tránh race) không được làm mất kết quả SOS đã thành công.
    if primary_contact:
        try:
            dispatch_kinh_action(
                db_path, serial_number, uuid.uuid4().hex, "call_emergency_contact",
                {"sos": True}, now.isoformat(),
            )
        except EmergencyContactNotFoundError:
            pass
    return result


def get_sos_event_by_token(db_path, location_token):
    """Xem vị trí qua link công khai (đã chốt §5.1: không cần đăng nhập). Hết hạn sau
    LOCATION_LINK_TTL_HOURS thì coi như không tìm thấy — không lộ thông tin 'link có tồn tại
    nhưng đã hết hạn' để tránh dò token."""
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT id, lat, lng, status, created_at FROM sos_event WHERE location_token = ?",
            (location_token,),
        ).fetchone()
        if not row:
            raise SosEventNotFoundError()
        created_at = datetime.fromisoformat(row["created_at"])
        if datetime.utcnow() - created_at > timedelta(hours=LOCATION_LINK_TTL_HOURS):
            raise SosEventNotFoundError()
        return dict(row)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Server Kính điều khiển hành động trên app điện thoại (SERVER_KINH_PROTOCOL.md mục C) —
# thiết kế đề xuất, đang implement phần backend (dispatch + report), app/Server Kính thật
# tích hợp sau.
# ---------------------------------------------------------------------------

def register_push_token(db_path, device_id, platform, push_token):
    """App điện thoại tự gọi khi khởi động/đăng nhập để backend biết gửi push đi đâu.
    1 device chỉ giữ 1 token hiện hành (chưa tính multi-device cùng account)."""
    conn = _connect(db_path)
    try:
        device = conn.execute("SELECT id FROM device WHERE id = ?", (device_id,)).fetchone()
        if not device:
            raise DeviceNotFoundError()
        now = datetime.utcnow().isoformat()
        conn.execute(
            "INSERT INTO device_push_token (device_id, platform, push_token, updated_at) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(device_id) DO UPDATE SET "
            "platform = excluded.platform, push_token = excluded.push_token, "
            "updated_at = excluded.updated_at",
            (device_id, platform, push_token, now),
        )
        conn.commit()
    finally:
        conn.close()


def dispatch_kinh_action(db_path, serial_number, request_id, action, params, timestamp_utc):
    """Server Kính gọi khi muốn app điện thoại tự thực hiện 1 hành động. `request_id` do
    Server Kính tự sinh — trùng với 1 lần gọi trước đó thì coi là retry, KHÔNG gửi push lại
    (idempotent, giống nguyên tắc idempotency đã áp dụng cho payment webhook).

    Với call_emergency_contact: backend tự tra emergency_contact và đính kèm tên+SĐT vào
    payload trước khi gửi push — Server Kính không cần biết danh sách liên hệ khẩn cấp (giữ
    đúng nguyên tắc đã áp dụng ở trigger_sos_from_device). Với call_contact, params.contact_query
    là text thô từ AI/STT — backend KHÔNG tự tra được vì đó là danh bạ máy, chỉ relay nguyên văn,
    app tự khớp và tự báo lại qua report_kinh_action_result nếu không tìm thấy (không ép gọi)."""
    if action not in KINH_ACTIONS:
        raise InvalidKinhActionError()
    conn = _connect(db_path)
    try:
        device = conn.execute(
            "SELECT id, account_id FROM device WHERE serial_number = ?", (serial_number,)
        ).fetchone()
        if not device:
            raise DeviceNotFoundError()
        device_id = device["id"]
        account_id = device["account_id"]

        existing = conn.execute(
            "SELECT dispatch_status FROM kinh_action_request WHERE request_id = ?",
            (request_id,),
        ).fetchone()
        if existing:
            return {"request_id": request_id, "status": existing["dispatch_status"], "duplicate": True}

        push_params = dict(params or {})
        if action == "call_emergency_contact":
            contact_id = push_params.pop("contact_id", None)
            if contact_id:
                contact = conn.execute(
                    "SELECT name, phone FROM emergency_contact WHERE id = ? AND account_id = ?",
                    (contact_id, account_id),
                ).fetchone()
            else:
                contact = conn.execute(
                    "SELECT name, phone FROM emergency_contact WHERE account_id = ? AND is_primary = 1",
                    (account_id,),
                ).fetchone()
            if not contact:
                raise EmergencyContactNotFoundError()
            # merge (không ghi đè) — giữ lại các key khác caller đã gửi kèm (vd. "sos": True
            # từ trigger_sos_from_device, quyết định 2026-08-02) để app phân biệt được ngữ cảnh.
            push_params.update({"contact_name": contact["name"], "contact_phone": contact["phone"]})
        elif action in ("navigate", "book_grab"):
            # Quyết định 2026-08-03: KHÔNG còn nhận params.destination tự do từ Server Kính —
            # chỉ dùng địa điểm đã lưu sẵn trong app (params.place, vd. "home") để tránh rủi ro
            # AI/STT nhận nhầm địa chỉ. Backend tự tra saved_place, đính lat/lng/address vào
            # payload push — Server Kính không cần biết toạ độ thật.
            place_key = push_params.pop("place", None)
            place = _get_saved_place_for_dispatch(conn, account_id, place_key)
            if not place:
                raise SavedPlaceNotFoundError()
            push_params["destination"] = {
                "lat": place["lat"], "lng": place["lng"], "address": place["address"],
            }

        push_row = conn.execute(
            "SELECT push_token FROM device_push_token WHERE device_id = ?", (device_id,)
        ).fetchone()
        now = datetime.utcnow().isoformat()
        status = "dispatched" if push_row else "no_push_token"
        conn.execute(
            "INSERT INTO kinh_action_request (request_id, device_id, action, params, "
            "dispatch_status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (request_id, device_id, action, json.dumps(push_params), status, now),
        )
        if push_row:
            # Mock provider (giống SIMULATING_SMS/PUSH_NOTIFICATION_SENT ở SOS) — TODO: thay
            # bằng gọi Firebase Admin SDK / APNs thật khi có credentials (SERVER_KINH_PROTOCOL.md §C.6).
            logger.info(
                f"SIMULATING_PUSH_ACTION to device {serial_number}: "
                f"action={action} params={json.dumps(push_params)} request_id={request_id}"
            )
        else:
            logger.info(
                f"No push token registered for device {serial_number} — action {action} not delivered."
            )
        conn.commit()
        return {"request_id": request_id, "status": status, "duplicate": False}
    finally:
        conn.close()


def report_kinh_action_result(db_path, device_id, request_id, status, detail):
    """App điện thoại tự báo kết quả xử lý hành động về backend — có thể gọi nhiều lần cho
    cùng request_id (vd. book_grab: đặt xe -> tài xế nhận -> tài xế đang tới, mỗi lần 1 status/detail
    mới, backend lưu lại toàn bộ lịch sử report)."""
    if status not in KINH_ACTION_REPORT_STATUSES:
        raise ValueError("status không hợp lệ")
    conn = _connect(db_path)
    try:
        req = conn.execute(
            "SELECT request_id FROM kinh_action_request WHERE request_id = ? AND device_id = ?",
            (request_id, device_id),
        ).fetchone()
        if not req:
            raise KinhActionRequestNotFoundError()
        conn.execute(
            "INSERT INTO kinh_action_report (id, request_id, status, detail, reported_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (uuid.uuid4().hex, request_id, status, detail, datetime.utcnow().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def get_kinh_action_result(db_path, request_id):
    """Server Kính poll lại kết quả xử lý 1 action (SERVER_KINH_PROTOCOL.md mục 3.3) — vd. để
    đọc to qua kính "không tìm thấy liên hệ mẹ". Trả về TOÀN BỘ lịch sử report (có thể nhiều
    dòng cho book_grab: đặt xe -> tài xế nhận -> tài xế đang tới), mới nhất ở cuối danh sách."""
    conn = _connect(db_path)
    try:
        req = conn.execute(
            "SELECT request_id, action, dispatch_status FROM kinh_action_request "
            "WHERE request_id = ?",
            (request_id,),
        ).fetchone()
        if not req:
            raise KinhActionRequestNotFoundError()
        reports = conn.execute(
            "SELECT status, detail, reported_at FROM kinh_action_report "
            "WHERE request_id = ? ORDER BY reported_at ASC",
            (request_id,),
        ).fetchall()
        return {
            "request_id": req["request_id"],
            "action": req["action"],
            "dispatch_status": req["dispatch_status"],
            "reports": [dict(r) for r in reports],
        }
    finally:
        conn.close()


def get_pending_kinh_actions(db_path, device_id):
    """App tự poll định kỳ (quyết định 2026-08-02, xem BACKEND_FLOWS.md §5.1e) để biết có
    action nào Server Kính vừa dispatch cho thiết bị này mà app CHƯA report kết quả — thay thế
    kênh push (Expo Go không nhận được remote push thật, kể cả khi có nối Firebase). 1 action
    coi là 'pending' nếu chưa có dòng nào trong kinh_action_report ứng với request_id đó. Trả
    mới nhất trước — app xử lý xong 1 cái (gọi .../report) thì lần poll sau nó biến mất khỏi
    danh sách này."""
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT request_id, action, params, created_at FROM kinh_action_request "
            "WHERE device_id = ? AND request_id NOT IN "
            "(SELECT request_id FROM kinh_action_report) "
            "ORDER BY created_at DESC",
            (device_id,),
        ).fetchall()
        pending = []
        for row in rows:
            item = dict(row)
            item["params"] = json.loads(item["params"])
            pending.append(item)
        return pending
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Theo dõi vị trí (BACKEND_FLOWS.md §5.2) — ghi liên tục định kỳ (đã chốt Task 4,
# khớp màn AN TOÀN luôn hiển thị "vị trí hiện tại").
# ---------------------------------------------------------------------------

def _haversine_meters(lat1, lng1, lat2, lng2):
    radius = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def report_location(db_path, device_id, lat, lng):
    conn = _connect(db_path)
    try:
        device = conn.execute(
            "SELECT account_id FROM device WHERE id = ?", (device_id,)
        ).fetchone()
        if not device:
            raise DeviceNotFoundError()
        conn.execute(
            "INSERT INTO location_log (id, account_id, lat, lng, recorded_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (uuid.uuid4().hex, device["account_id"], lat, lng, datetime.utcnow().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def get_current_location(db_path, account_id):
    """Vị trí hiện tại + trạng thái 'Đang di chuyển'/'Đứng yên' (so 2 điểm gần nhất,
    ngưỡng LOCATION_MOVING_THRESHOLD_METERS — placeholder, xem §5.2)."""
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT lat, lng, recorded_at FROM location_log WHERE account_id = ? "
            "ORDER BY recorded_at DESC LIMIT 2",
            (account_id,),
        ).fetchall()
        if not rows:
            return None
        latest = rows[0]
        status = "Đứng yên"
        if len(rows) == 2:
            distance = _haversine_meters(
                latest["lat"], latest["lng"], rows[1]["lat"], rows[1]["lng"]
            )
            if distance >= LOCATION_MOVING_THRESHOLD_METERS:
                status = "Đang di chuyển"
        return {
            "lat": latest["lat"],
            "lng": latest["lng"],
            "status": status,
            "updated_at": latest["recorded_at"],
        }
    finally:
        conn.close()


def purge_old_location_logs(db_path, older_than_days=None):
    """Chính sách retention (§5.2) — xoá location_log cũ hơn LOCATION_LOG_RETENTION_DAYS.
    Chưa có cơ chế tự động gọi định kỳ (cron) — cần gọi tay hoặc lên lịch riêng."""
    days = older_than_days if older_than_days is not None else LOCATION_LOG_RETENTION_DAYS
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    conn = _connect(db_path)
    try:
        cursor = conn.execute("DELETE FROM location_log WHERE recorded_at < ?", (cutoff,))
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Nhật ký hoạt động (BACKEND_FLOWS.md §5.3) — ghi thủ công qua API (đã chốt Task 4),
# CHƯA có auto-detect điểm đến (geofencing/POI), đó là bài toán AI/bản đồ riêng.
# ---------------------------------------------------------------------------

def add_activity_log_entry(db_path, account_id, title):
    conn = _connect(db_path)
    try:
        conn.execute(
            "INSERT INTO activity_log_entry (id, account_id, title, recorded_at) "
            "VALUES (?, ?, ?, ?)",
            (uuid.uuid4().hex, account_id, title, datetime.utcnow().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def get_activity_log(db_path, account_id, limit=20):
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT title, recorded_at FROM activity_log_entry WHERE account_id = ? "
            "ORDER BY recorded_at DESC LIMIT ?",
            (account_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Community Module (BACKEND_FLOWS.md §6) — nhóm/sự kiện là nội dung tĩnh do admin nạp
# (seed_content.py), người dùng chỉ tham gia/lưu, không tự tạo nhóm hay sự kiện.
# ---------------------------------------------------------------------------

def add_community_group(db_path, name, description=None):
    conn = _connect(db_path)
    try:
        group_id = uuid.uuid4().hex
        conn.execute(
            "INSERT INTO community_group (id, name, description) VALUES (?, ?, ?)",
            (group_id, name, description),
        )
        conn.commit()
        return group_id
    finally:
        conn.close()


def list_community_groups(db_path):
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT g.id, g.name, g.description, COUNT(m.account_id) AS member_count "
            "FROM community_group g LEFT JOIN group_membership m ON m.group_id = g.id "
            "GROUP BY g.id ORDER BY g.name ASC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def join_community_group(db_path, account_id, group_id):
    """Tự do tham gia, KHÔNG cần admin duyệt (đã chốt Task 8)."""
    conn = _connect(db_path)
    try:
        if not conn.execute(
            "SELECT 1 FROM community_group WHERE id = ?", (group_id,)
        ).fetchone():
            raise GroupNotFoundError()
        conn.execute(
            "INSERT OR IGNORE INTO group_membership (account_id, group_id, joined_at) "
            "VALUES (?, ?, ?)",
            (account_id, group_id, datetime.utcnow().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def add_community_post(db_path, account_id, author_name, title, content):
    """Hiển thị NGAY, không kiểm duyệt trước (đã chốt Task 8 — post-moderation, admin xoá
    sau nếu vi phạm, không chặn trước khi đăng)."""
    conn = _connect(db_path)
    try:
        post_id = uuid.uuid4().hex
        conn.execute(
            "INSERT INTO community_post (id, account_id, author_name, title, content, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (post_id, account_id, author_name, title, content, datetime.utcnow().isoformat()),
        )
        conn.commit()
        return post_id
    finally:
        conn.close()


def list_community_posts(db_path, limit=20):
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT id, author_name, title, content, created_at FROM community_post "
            "ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_community_event(db_path, title, event_time, location=None):
    conn = _connect(db_path)
    try:
        event_id = uuid.uuid4().hex
        conn.execute(
            "INSERT INTO community_event (id, title, event_time, location) VALUES (?, ?, ?, ?)",
            (event_id, title, event_time, location),
        )
        conn.commit()
        return event_id
    finally:
        conn.close()


def list_community_events(db_path):
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT id, title, event_time, location FROM community_event ORDER BY event_time ASC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def save_event(db_path, account_id, event_id):
    """Lưu sự kiện — KHÔNG có nhắc nhở tự động (đã chốt Task 8, nhất quán 'không thêm
    scheduler mới' như các phần khác chưa có cron)."""
    conn = _connect(db_path)
    try:
        if not conn.execute(
            "SELECT 1 FROM community_event WHERE id = ?", (event_id,)
        ).fetchone():
            raise EventNotFoundError()
        conn.execute(
            "INSERT OR IGNORE INTO saved_event (account_id, event_id, saved_at) VALUES (?, ?, ?)",
            (account_id, event_id, datetime.utcnow().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def unsave_event(db_path, account_id, event_id):
    conn = _connect(db_path)
    try:
        conn.execute(
            "DELETE FROM saved_event WHERE account_id = ? AND event_id = ?",
            (account_id, event_id),
        )
        conn.commit()
    finally:
        conn.close()


def list_saved_events(db_path, account_id):
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT e.id, e.title, e.event_time, e.location FROM saved_event s "
            "JOIN community_event e ON e.id = s.event_id WHERE s.account_id = ? "
            "ORDER BY e.event_time ASC",
            (account_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Support Module (BACKEND_FLOWS.md §7)
# ---------------------------------------------------------------------------

def add_support_article(db_path, kind, title, body):
    """kind: 'guide' (Hướng dẫn sử dụng) hoặc 'faq' — nội dung tĩnh do admin quản lý
    (seed_content.py), không phải dữ liệu người dùng tạo."""
    conn = _connect(db_path)
    try:
        article_id = uuid.uuid4().hex
        conn.execute(
            "INSERT INTO support_article (id, kind, title, body) VALUES (?, ?, ?, ?)",
            (article_id, kind, title, body),
        )
        conn.commit()
        return article_id
    finally:
        conn.close()


def list_support_articles(db_path, kind=None):
    conn = _connect(db_path)
    try:
        if kind:
            rows = conn.execute(
                "SELECT id, kind, title, body FROM support_article WHERE kind = ?", (kind,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT id, kind, title, body FROM support_article").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def create_support_ticket(db_path, account_id, category, description):
    """category: 'bug_report' (Phản hồi lỗi) hoặc 'support_request' (Gửi yêu cầu hỗ trợ).
    Trường tối thiểu, KHÔNG đính kèm file/ảnh (đã chốt Task 8 — chưa có hạ tầng lưu file)."""
    if category not in SUPPORT_TICKET_CATEGORIES:
        raise ValueError(f"category phải là một trong {SUPPORT_TICKET_CATEGORIES}")
    conn = _connect(db_path)
    try:
        ticket_id = uuid.uuid4().hex
        conn.execute(
            "INSERT INTO support_ticket (id, account_id, category, description, status, "
            "created_at, resolved_at) VALUES (?, ?, ?, ?, 'open', ?, NULL)",
            (ticket_id, account_id, category, description, datetime.utcnow().isoformat()),
        )
        conn.commit()
        return ticket_id
    finally:
        conn.close()


def list_own_support_tickets(db_path, account_id):
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            "SELECT id, category, description, status, created_at, resolved_at "
            "FROM support_ticket WHERE account_id = ? ORDER BY created_at DESC",
            (account_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def list_all_support_tickets(db_path, status=None):
    """Dùng cho đội hỗ trợ xử lý — gate bằng cờ is_admin (tái dùng, chưa tách role
    'support' riêng, xem BACKEND_FLOWS §7.2)."""
    conn = _connect(db_path)
    try:
        if status:
            rows = conn.execute(
                "SELECT id, account_id, category, description, status, created_at, resolved_at "
                "FROM support_ticket WHERE status = ? ORDER BY created_at ASC",
                (status,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, account_id, category, description, status, created_at, resolved_at "
                "FROM support_ticket ORDER BY created_at ASC"
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_support_ticket_status(db_path, ticket_id, status):
    if status not in SUPPORT_TICKET_STATUSES:
        raise ValueError(f"status phải là một trong {SUPPORT_TICKET_STATUSES}")
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT account_id, status AS old_status FROM support_ticket WHERE id = ?",
            (ticket_id,),
        ).fetchone()
        if not row:
            raise TicketNotFoundError()
        resolved_at = datetime.utcnow().isoformat() if status == "resolved" else None
        conn.execute(
            "UPDATE support_ticket SET status = ?, resolved_at = ? WHERE id = ?",
            (status, resolved_at, ticket_id),
        )
        conn.commit()
        account_id, old_status = row["account_id"], row["old_status"]
    finally:
        conn.close()
    # Gửi SMS SAU khi đã commit — đóng gap "chưa gửi thông báo lại cho người dùng khi đổi
    # trạng thái" (API_CONTRACT.md mục Support, quyết định 2026-08-02). Chỉ gửi khi status
    # thực sự đổi (PATCH gửi lại đúng status cũ không nên làm phiền người dùng).
    if status != old_status:
        account = get_account_by_id(db_path, account_id)
        if account:
            status_label = {
                "open": "Đang mở", "in_progress": "Đang xử lý", "resolved": "Đã xử lý xong",
            }[status]
            _send_sms(
                account["phone"],
                f"Ticket hỗ trợ #{ticket_id[:8]} của bạn vừa chuyển sang trạng thái: {status_label}.",
            )


def log_hotline_call(db_path, account_id=None):
    """Log lượt bấm gọi hotline tĩnh (1900 1234) để đo nhu cầu hỗ trợ trực tiếp
    (BACKEND_FLOWS §7.3) — account_id có thể None nếu gọi không cần đăng nhập."""
    conn = _connect(db_path)
    try:
        conn.execute(
            "INSERT INTO hotline_call_log (id, account_id, called_at) VALUES (?, ?, ?)",
            (uuid.uuid4().hex, account_id, datetime.utcnow().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()
