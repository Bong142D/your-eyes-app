import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Phải set TRƯỚC khi import app — scheduler khởi động ngay lúc import module (mức module-level,
# xem app.py::_start_background_scheduler), monkeypatch trong fixture chạy quá trễ để chặn.
# Không tắt sẽ khiến mỗi lần chạy test đều thật sự bật 1 thread nền gọi
# retry_failed_notifications/scan_and_notify_expired_subscriptions.
os.environ["SCHEDULER_ENABLED"] = "false"

# Cùng lý do — app.py::_sync_schema_on_startup() (mới 2026-08-02) cũng chạy ngay lúc import
# module, TRƯỚC khi fixture db_path kịp set BILLING_DB_PATH riêng cho từng test. Không trỏ tạm
# ra đây thì nó sẽ tạo 1 file billing_data.db thật ngay trong thư mục backend/billing/ (đường
# dẫn mặc định của get_db_path) mỗi lần chạy test — rác lặp lại y hệt lỗi đã dọn tay 2 lần
# trước đó trong ngày. File tạm này không test nào dùng tới sau đó (mỗi test tự có path riêng
# qua fixture db_path).
os.environ["BILLING_DB_PATH"] = os.path.join(tempfile.gettempdir(), "your_eyes_conftest_import.db")

import app as billing_app  # noqa: E402
import models  # noqa: E402

TEST_SERIALS = ["YE-TEST-0001", "YE-TEST-0002", "YE-TEST-0003", "YE-TEST-0004", "YE-TEST-0005"]


class _DefaultFakeGlassesResponse:
    status_code = 200
    text = ""


@pytest.fixture(autouse=True)
def _no_real_network_to_glasses_server(monkeypatch):
    """Mọi hành động (link_device, thanh toán, refund...) đều tự bắn notify ra Server Kính
    (Task 7). KHÔNG mock mặc định sẽ khiến MỌI test gọi mạng thật ra localhost:5004 (không
    ai lắng nghe) — vừa chậm vừa nhiễu log. Test nào cần kiểm tra hành vi thất bại/retry cứ
    tự monkeypatch models.requests.post đè lên cái này trong thân test (áp dụng sau, được ưu
    tiên nhờ cùng 1 monkeypatch fixture theo test)."""
    monkeypatch.setattr(
        models.requests, "post", lambda *args, **kwargs: _DefaultFakeGlassesResponse()
    )


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = str(tmp_path / "test_billing.db")
    monkeypatch.setenv("BILLING_DB_PATH", path)
    monkeypatch.setenv("BILLING_ENV", "dev")
    models.init_db(path)
    for serial in TEST_SERIALS:
        models.add_catalog_serial(path, serial)
    return path


@pytest.fixture
def client(db_path):
    return billing_app.app.test_client()
