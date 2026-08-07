import models


def test_create_account_and_lookup(tmp_path):
    db_path = str(tmp_path / "test.db")
    models.init_db(db_path)
    account_id = models.create_account(db_path, "0900000010")
    assert account_id
    account = models.get_account_by_phone(db_path, "0900000010")
    assert account["id"] == account_id
    assert account["phone"] == "0900000010"


def test_create_account_duplicate_phone_raises(tmp_path):
    db_path = str(tmp_path / "test.db")
    models.init_db(db_path)
    models.create_account(db_path, "0900000011")
    try:
        models.create_account(db_path, "0900000011")
        assert False, "phải raise ValueError khi số điện thoại đã tồn tại"
    except ValueError:
        pass


def test_get_account_by_phone_not_found_returns_none(tmp_path):
    db_path = str(tmp_path / "test.db")
    models.init_db(db_path)
    assert models.get_account_by_phone(db_path, "0900000012") is None


def test_create_session_and_lookup(tmp_path):
    db_path = str(tmp_path / "test.db")
    models.init_db(db_path)
    account_id = models.create_account(db_path, "0900000013")
    token = models.create_session(db_path, account_id)
    assert models.get_account_id_by_token(db_path, token) == account_id


def test_revoke_session_invalidates_token(tmp_path):
    db_path = str(tmp_path / "test.db")
    models.init_db(db_path)
    account_id = models.create_account(db_path, "0900000014")
    token = models.create_session(db_path, account_id)
    models.revoke_session(db_path, token)
    assert models.get_account_id_by_token(db_path, token) is None


def test_get_account_id_by_token_unknown_returns_none(tmp_path):
    db_path = str(tmp_path / "test.db")
    models.init_db(db_path)
    assert models.get_account_id_by_token(db_path, "not-a-real-token") is None