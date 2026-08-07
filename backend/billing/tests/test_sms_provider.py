import logging

import models


def _configure_twilio(monkeypatch):
    monkeypatch.setattr(models, "TWILIO_ACCOUNT_SID", "AC_test_sid")
    monkeypatch.setattr(models, "TWILIO_AUTH_TOKEN", "test_auth_token")
    monkeypatch.setattr(models, "TWILIO_FROM_NUMBER", "+15551234567")


class _FakeMessages:
    def __init__(self, calls, should_raise):
        self._calls = calls
        self._should_raise = should_raise

    def create(self, body, from_, to):
        if self._should_raise:
            raise RuntimeError("Twilio API error")
        self._calls.append({"kind": "sms", "body": body, "from_": from_, "to": to})


class _FakeCalls:
    def __init__(self, calls, should_raise):
        self._calls = calls
        self._should_raise = should_raise

    def create(self, to, from_, twiml):
        if self._should_raise:
            raise RuntimeError("Twilio API error")
        self._calls.append({"kind": "call", "twiml": twiml, "from_": from_, "to": to})


def _fake_client_factory(calls, should_raise=False):
    class _FakeClient:
        def __init__(self, sid, token):
            self.messages = _FakeMessages(calls, should_raise)
            self.calls = _FakeCalls(calls, should_raise)

    return _FakeClient


# ---------------------------------------------------------------------------
# _to_e164
# ---------------------------------------------------------------------------

def test_to_e164_converts_local_vn_number():
    assert models._to_e164("0912345678") == "+84912345678"


def test_to_e164_leaves_already_e164_unchanged():
    assert models._to_e164("+84912345678") == "+84912345678"


# ---------------------------------------------------------------------------
# _send_sms / _make_robocall — fallback to mock when Twilio not configured
# ---------------------------------------------------------------------------

def test_send_sms_falls_back_to_mock_when_not_configured(caplog):
    caplog.set_level(logging.INFO, logger="models")
    result = models._send_sms("0912345678", "hello")
    assert result is False
    assert any("SIMULATING_SMS" in r.message for r in caplog.records)


def test_make_robocall_falls_back_to_mock_when_not_configured(caplog):
    caplog.set_level(logging.INFO, logger="models")
    result = models._make_robocall("0912345678", "hello")
    assert result is False
    assert any("SIMULATING_ROBO_CALL" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# _send_sms / _make_robocall — real Twilio path (Client mocked, no real network)
# ---------------------------------------------------------------------------

def test_send_sms_uses_twilio_when_configured(monkeypatch):
    _configure_twilio(monkeypatch)
    calls = []
    monkeypatch.setattr("twilio.rest.Client", _fake_client_factory(calls))

    result = models._send_sms("0912345678", "Mã OTP của bạn là 123456")

    assert result is True
    assert len(calls) == 1
    assert calls[0]["kind"] == "sms"
    assert calls[0]["to"] == "+84912345678"
    assert calls[0]["from_"] == "+15551234567"
    assert "123456" in calls[0]["body"]


def test_send_sms_returns_false_on_twilio_error(monkeypatch, caplog):
    _configure_twilio(monkeypatch)
    caplog.set_level(logging.INFO, logger="models")
    monkeypatch.setattr("twilio.rest.Client", _fake_client_factory([], should_raise=True))

    result = models._send_sms("0912345678", "hello")

    assert result is False
    assert any("TWILIO_SMS_FAILED" in r.message for r in caplog.records)


def test_make_robocall_uses_twilio_when_configured(monkeypatch):
    _configure_twilio(monkeypatch)
    calls = []
    monkeypatch.setattr("twilio.rest.Client", _fake_client_factory(calls))

    result = models._make_robocall("0912345678", "khẩn cấp")

    assert result is True
    assert len(calls) == 1
    assert calls[0]["kind"] == "call"
    assert calls[0]["to"] == "+84912345678"
    assert "khẩn cấp" in calls[0]["twiml"]


# ---------------------------------------------------------------------------
# generate_otp actually sends the code via SMS
# ---------------------------------------------------------------------------

def test_generate_otp_sends_sms_with_the_code(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    models.init_db(db_path)

    sent = []
    monkeypatch.setattr(
        models, "_send_sms",
        lambda phone, message: sent.append((phone, message)) or True,
    )

    otp = models.generate_otp(db_path, "0912345678", purpose="register")

    assert len(sent) == 1
    assert sent[0][0] == "0912345678"
    assert otp["code"] in sent[0][1]


# ---------------------------------------------------------------------------
# SOS delivery status reflects real Twilio outcome (not hardcoded "sent")
# ---------------------------------------------------------------------------

def test_sos_delivery_marked_failed_when_twilio_sms_errors(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    models.init_db(db_path)
    account_id = models.create_account(db_path, "0955512345")
    models.add_catalog_serial(db_path, "YE-SMS-TEST-0001")
    models.link_device(db_path, account_id, "YE-SMS-TEST-0001")
    models.add_emergency_contact(db_path, account_id, "Mẹ", "0911111111", True)

    _configure_twilio(monkeypatch)
    monkeypatch.setattr("twilio.rest.Client", _fake_client_factory([], should_raise=True))

    result = models.trigger_sos_from_device(db_path, "YE-SMS-TEST-0001", 10.0, 106.0)

    sms_deliveries = [d for d in result["deliveries"] if d["channel"] == "sms"]
    assert sms_deliveries[0]["status"] == "failed"


def test_sos_delivery_marked_sent_when_twilio_sms_succeeds(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    models.init_db(db_path)
    account_id = models.create_account(db_path, "0955512346")
    models.add_catalog_serial(db_path, "YE-SMS-TEST-0002")
    models.link_device(db_path, account_id, "YE-SMS-TEST-0002")
    models.add_emergency_contact(db_path, account_id, "Mẹ", "0911111111", True)

    _configure_twilio(monkeypatch)
    calls = []
    monkeypatch.setattr("twilio.rest.Client", _fake_client_factory(calls))

    result = models.trigger_sos_from_device(db_path, "YE-SMS-TEST-0002", 10.0, 106.0)

    sms_deliveries = [d for d in result["deliveries"] if d["channel"] == "sms"]
    robocall_deliveries = [d for d in result["deliveries"] if d["channel"] == "robocall"]
    assert sms_deliveries[0]["status"] == "sent"
    assert robocall_deliveries[0]["status"] == "sent"
    assert any(c["kind"] == "sms" for c in calls)
    assert any(c["kind"] == "call" for c in calls)
