import pytest

from app import database


def test_database_url_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(database, "DATABASE_URL", "")

    with pytest.raises(RuntimeError, match="DATABASE_URL es obligatorio"):
        database._connect_postgres()
