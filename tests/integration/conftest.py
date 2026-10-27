import os
from collections.abc import Generator

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from tests.database_safety import validate_test_database_url

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/tokenledger_test",
)

# Ensure DATABASE_URL points to test database for tests
os.environ["DATABASE_URL"] = TEST_DATABASE_URL


@pytest.fixture(scope="session", autouse=True)
def setup_test_db() -> None:
    test_url = validate_test_database_url(TEST_DATABASE_URL)
    # 1. Ensure test database exists in postgres
    admin_url = test_url.set(database="postgres")
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        with admin_engine.connect() as conn:
            res = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :database"),
                {"database": test_url.database},
            )
            if not res.scalar():
                name = admin_engine.dialect.identifier_preparer.quote(test_url.database)
                conn.execute(text(f"CREATE DATABASE {name}"))
    finally:
        admin_engine.dispose()

    # 2. Clear settings cache to pick up TEST_DATABASE_URL
    from app.core.config import get_settings

    get_settings.cache_clear()

    # 3. Run Alembic upgrade head
    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")


@pytest.fixture(scope="session")
def test_engine(setup_test_db: None) -> Generator[Engine, None, None]:
    engine = create_engine(
        validate_test_database_url(TEST_DATABASE_URL), pool_pre_ping=True
    )
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(test_engine: Engine) -> Generator[Session, None, None]:
    # Clean tables before each test
    validate_test_database_url(test_engine.url)
    with test_engine.connect() as conn:
        conn.execute(text("TRUNCATE TABLE events, prices RESTART IDENTITY CASCADE;"))
        conn.commit()

    SessionTest = sessionmaker(
        bind=test_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    with SessionTest() as session:
        yield session
