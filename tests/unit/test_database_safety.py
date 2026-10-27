import pytest
from sqlalchemy.engine import make_url

from tests.database_safety import validate_test_database_url


@pytest.mark.parametrize("host", ["localhost", "127.0.0.1", "db"])
def test_local_test_database_is_allowed(host: str) -> None:
    url = make_url(f"postgresql+psycopg://user:synthetic@{host}:5544/custom_test")
    validated = validate_test_database_url(url)
    assert validated == url
    admin = validated.set(database="postgres")
    assert admin.host == host
    assert admin.port == 5544
    assert admin.username == "user"
    assert admin.password == "synthetic"
    assert admin.database == "postgres"


@pytest.mark.parametrize(
    "target",
    [
        "localhost/production",
        "db/tokenledger",
        "remote.invalid/project_test",
        "localhost.evil.invalid/project_test",
        "localhost/",
        "localhost/project_test?host=remote.invalid",
        "localhost/project_test?dbname=production",
    ],
)
def test_unsafe_database_is_rejected_without_echoing_credentials(target: str) -> None:
    with pytest.raises(ValueError, match="_test.*localhost.*127.0.0.1.*db") as exc:
        validate_test_database_url(f"postgresql+psycopg://user:synthetic@{target}")
    assert "synthetic" not in str(exc.value)


def test_truncate_guard_checks_engine_before_connecting() -> None:
    from unittest.mock import MagicMock

    from tests.integration.conftest import db_session

    engine = MagicMock(url=make_url("postgresql+psycopg://localhost/production"))
    with pytest.raises(ValueError, match="_test"):
        next(db_session.__wrapped__(engine))
    engine.connect.assert_not_called()


def test_admin_connection_uses_configured_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from unittest.mock import MagicMock

    from alembic import command

    from tests.integration import conftest

    url = "postgresql+psycopg://custom:synthetic@db:5544/custom_test"
    factory = MagicMock()
    monkeypatch.setattr(conftest, "TEST_DATABASE_URL", url)
    monkeypatch.setattr(conftest, "create_engine", factory)
    monkeypatch.setattr(command, "upgrade", MagicMock())
    conftest.setup_test_db.__wrapped__()
    factory.assert_called_once_with(
        make_url(url).set(database="postgres"), isolation_level="AUTOCOMMIT"
    )


def test_setup_guard_runs_before_connecting(monkeypatch: pytest.MonkeyPatch) -> None:
    from unittest.mock import MagicMock

    from tests.integration import conftest

    factory = MagicMock()
    monkeypatch.setattr(conftest, "create_engine", factory)
    monkeypatch.setattr(
        conftest, "TEST_DATABASE_URL", "postgresql+psycopg://localhost/production"
    )
    with pytest.raises(ValueError, match="_test"):
        conftest.setup_test_db.__wrapped__()
    factory.assert_not_called()
