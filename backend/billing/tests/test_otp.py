import models


def test_generate_otp_within_cooldown_raises(tmp_path):
    db_path = str(tmp_path / "test.db")
    models.init_db(db_path)
    models.generate_otp(db_path, "0911111111", purpose="register")
    try:
        models.generate_otp(db_path, "0911111111", purpose="register")
        assert False, "phải raise OtpCooldownError khi gửi lại quá sớm"
    except models.OtpCooldownError:
        pass


def test_verify_otp_unknown_phone_raises_not_found(tmp_path):
    db_path = str(tmp_path / "test.db")
    models.init_db(db_path)
    try:
        models.verify_otp(db_path, "0922222222", "123456", purpose="register")
        assert False, "phải raise OtpNotFoundError khi chưa từng gửi OTP"
    except models.OtpNotFoundError:
        pass


def test_verify_otp_too_many_attempts_raises(tmp_path):
    db_path = str(tmp_path / "test.db")
    models.init_db(db_path)
    models.generate_otp(db_path, "0933333333", purpose="register")
    for _ in range(models.OTP_MAX_ATTEMPTS):
        try:
            models.verify_otp(db_path, "0933333333", "000000", purpose="register")
        except models.OtpInvalidError:
            pass
    try:
        models.verify_otp(db_path, "0933333333", "000000", purpose="register")
        assert False, "phải raise OtpTooManyAttemptsError sau khi vượt số lần cho phép"
    except models.OtpTooManyAttemptsError:
        pass


def test_verify_otp_correct_code_succeeds(tmp_path):
    db_path = str(tmp_path / "test.db")
    models.init_db(db_path)
    otp = models.generate_otp(db_path, "0944444444", purpose="register")
    assert models.verify_otp(db_path, "0944444444", otp["code"], purpose="register") is True


def test_verify_otp_already_consumed_raises_not_found(tmp_path):
    db_path = str(tmp_path / "test.db")
    models.init_db(db_path)
    otp = models.generate_otp(db_path, "0955555555", purpose="register")
    models.verify_otp(db_path, "0955555555", otp["code"], purpose="register")
    try:
        models.verify_otp(db_path, "0955555555", otp["code"], purpose="register")
        assert False, "phải raise OtpNotFoundError khi OTP đã dùng rồi"
    except models.OtpNotFoundError:
        pass
