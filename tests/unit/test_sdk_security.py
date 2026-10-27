import logging
import queue
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

from sdk.tokenledger import TokenLedger

SENTINEL = "sk-test-SENTINEL-123"


def assert_secret_hidden(sdk: TokenLedger, caplog: pytest.LogCaptureFixture) -> None:
    assert SENTINEL not in caplog.text
    for record in caplog.records:
        assert SENTINEL not in logging.Formatter().format(record)
        assert SENTINEL not in (record.exc_text or "")
        if record.exc_info:
            assert SENTINEL not in logging.Formatter().formatException(record.exc_info)
        assert record.exc_info is None
    for representation in (repr(sdk), str(sdk)):
        assert SENTINEL not in representation
        assert "api_key=***" in representation


@pytest.mark.parametrize(
    "error_type", [RuntimeError, httpx.HTTPError, httpx.ReadTimeout]
)
def test_transport_exception_is_sanitized(
    error_type: type[Exception], caplog: pytest.LogCaptureFixture
) -> None:
    def fail(request: httpx.Request) -> httpx.Response:
        key = request.headers["X-API-Key"]
        raise error_type(f"transport failed: {key}; repeated: {key}")

    with httpx.Client(transport=httpx.MockTransport(fail)) as client:
        sdk = TokenLedger("http://test-api", SENTINEL, http_client=client)
        response = SimpleNamespace(
            model="test-model",
            usage=SimpleNamespace(input_tokens=1, output_tokens=1),
        )
        with caplog.at_level(logging.WARNING, logger="tokenledger"):
            try:
                assert sdk.track(lambda: response, "anthropic", "test") is response
                sdk.flush()
            finally:
                sdk.close()
        assert caplog.records
        assert_secret_hidden(sdk, caplog)
        assert error_type.__name__ in caplog.text
        assert "transport failed: ***; repeated: ***" in caplog.text


def test_worker_exception_is_sanitized(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    with httpx.Client() as client:
        sdk = TokenLedger("http://test-api", SENTINEL, http_client=client)

        def fail(payload: dict[str, Any]) -> None:
            raise RuntimeError(f"worker failed: {SENTINEL}")

        monkeypatch.setattr(sdk, "_post_event", fail)
        with caplog.at_level(logging.WARNING, logger="tokenledger"):
            sdk._enqueue({"model": "test-model"})
            sdk.flush()
            sdk.close()
        assert_secret_hidden(sdk, caplog)
        assert "RuntimeError" in caplog.text
        assert "worker failed: ***" in caplog.text


@pytest.mark.parametrize("status", [401, 422, 500])
def test_error_response_does_not_log_secret(
    status: int, caplog: pytest.LogCaptureFixture
) -> None:
    def reject(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, text=request.headers["X-API-Key"])

    with httpx.Client(transport=httpx.MockTransport(reject)) as client:
        sdk = TokenLedger("http://test-api", SENTINEL, http_client=client)
        response = SimpleNamespace(
            model=SENTINEL, usage=SimpleNamespace(input_tokens=1, output_tokens=1)
        )
        with caplog.at_level(logging.WARNING, logger="tokenledger"):
            assert sdk.track(lambda: response, "anthropic", "test") is response
            sdk.flush()
            sdk.close()
        assert str(status) in caplog.text
        assert_secret_hidden(sdk, caplog)


def test_full_queue_warning_does_not_log_secret(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    with httpx.Client() as client:
        sdk = TokenLedger("http://test-api", SENTINEL, http_client=client)

        def full(payload: dict[str, Any]) -> None:
            raise queue.Full(SENTINEL)

        with monkeypatch.context() as patch:
            patch.setattr(sdk._queue, "put_nowait", full)
            with caplog.at_level(logging.WARNING, logger="tokenledger"):
                sdk._enqueue({"model": SENTINEL})
                sdk.flush()
        sdk.close()
        assert "queue is full" in caplog.text
        assert_secret_hidden(sdk, caplog)
