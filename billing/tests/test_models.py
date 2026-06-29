import models


def test_create_account_and_lookup(tmp_path):
    db_path = str(tmp_path / "test.db")
    models.init_db(db_path)
    account_id = models.create_account(db_path, "user@example.com")
    assert account_id
    account = models.get_account_by_email(db_path, "user@example.com")
    assert account["id"] == account_id
    assert account["email"] == "user@example.com"


def test_create_account_duplicate_email_raises(tmp_path):
    db_path = str(tmp_path / "test.db")
    models.init_db(db_path)
    models.create_account(db_path, "dup@example.com")
    try:
        models.create_account(db_path, "dup@example.com")
        assert False, "phải raise ValueError khi email đã tồn tại"
    except ValueError:
        pass


def test_get_account_by_email_not_found_returns_none(tmp_path):
    db_path = str(tmp_path / "test.db")
    models.init_db(db_path)
    assert models.get_account_by_email(db_path, "nobody@example.com") is None