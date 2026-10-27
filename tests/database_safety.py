from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError


def validate_test_database_url(database_url: str | URL) -> URL:
    """Reject unsafe targets before any connection or destructive fixture SQL."""
    message = (
        "Unsafe test database: name must end in _test and host must be "
        "localhost, 127.0.0.1 or db; connection target overrides are forbidden."
    )
    try:
        url = make_url(database_url)
    except ArgumentError:
        raise ValueError(message) from None
    target_overrides = {
        "host",
        "hostaddr",
        "dbname",
        "database",
        "service",
        "servicefile",
    }
    if (
        (url.host or "").lower() not in {"localhost", "127.0.0.1", "db"}
        or not (url.database or "").endswith("_test")
        or target_overrides.intersection(key.lower() for key in url.query)
    ):
        raise ValueError(message)
    return url
