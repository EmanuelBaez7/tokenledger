import os
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/tokenledger_test",
)

# Ensure DATABASE_URL points to test database for tests
os.environ["DATABASE_URL"] = TEST_DATABASE_URL


@pytest.fixture(scope="session", autouse=True)
def setup_test_db() -> None:
    # 1. Ensure test database exists in postgres
    admin_url = "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/postgres"
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        res = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = 'tokenledger_test'")
        )
        if not res.scalar():
            conn.execute(text("CREATE DATABASE tokenledger_test"))
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
def test_engine(setup_test_db):
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(test_engine) -> Generator[Session, None, None]:
    # Clean tables before each test
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
