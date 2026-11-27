import pytest

from phai import config


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "MARKET_DB", tmp_path / "market.db")
    monkeypatch.setattr(config, "USER_DB", tmp_path / "user.db")
    from phai import db
    db.init_all()
    return tmp_path
