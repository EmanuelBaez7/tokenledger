"""Unit tests for sdk/tokenledger/client.py.

Uses SimpleNamespace objects to fake LLM responses and httpx.MockTransport
to intercept HTTP calls — no real API or LLM is called.
"""

from __future__ import annotations

import json
import logging
import queue
import threading
import time
from types import SimpleNamespace

import httpx
import pytest

from sdk.tokenledger.client import TokenLedger

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_anthropic_response(
    model: str = "claude-3-haiku-20240307",
    input_tokens: int = 500,
    output_tokens: int = 200,
) -> SimpleNamespace:
    """Fake Anthropic-style response."""
    return SimpleNamespace(
        model=model,
        usage=SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens),
    )


def _make_openai_response(
    model: str = "gpt-4o-mini",
    prompt_tokens: int = 300,
    completion_tokens: int = 100,
) -> SimpleNamespace:
    """Fake OpenAI-style response."""
    return SimpleNamespace(
        model=model,
        usage=SimpleNamespace(
            prompt_tokens=prompt_tokens, completion_tokens=completion_tokens
        ),
    )


class CapturedTransport:
    """Helper that creates an httpx.MockTransport capturing all request bodies."""

    def __init__(self) -> None:
        self.captured: list[dict] = []
        self._lock = threading.Lock()

        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            with self._lock:
                self.captured.append(body)
            return httpx.Response(201, json={"ok": True})

        self.transport = httpx.MockTransport(handler)


def make_fail_transport() -> httpx.MockTransport:
    """Helper that creates an httpx.MockTransport raising connection error."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    return httpx.MockTransport(handler)


def _make_sdk(transport: httpx.MockTransport | None = None) -> TokenLedger:
    if transport is None:
        transport = CapturedTransport().transport
    http_client = httpx.Client(transport=transport)
    return TokenLedger(
        base_url="http://test-api:8000",
        api_key="test-key",
        timeout=1.0,
        http_client=http_client,
    )


# ---------------------------------------------------------------------------
# Basic track behaviour
# ---------------------------------------------------------------------------


def test_track_returns_original_response() -> None:
    """track() must return exactly the same object returned by fn."""
    cap_trans = CapturedTransport()
    sdk = _make_sdk(cap_trans.transport)
    fake_resp = _make_anthropic_response()

    result = sdk.track(lambda: fake_resp, provider="anthropic", feature="resumen")
    sdk.flush()

    assert result is fake_resp
    sdk.close()


def test_track_anthropic_sends_correct_event() -> None:
    """Anthropic response: correct tokens extracted and posted."""
    cap_trans = CapturedTransport()
    sdk = _make_sdk(cap_trans.transport)
    fake_resp = _make_anthropic_response(
        model="claude-3-haiku-20240307", input_tokens=1000, output_tokens=400
    )

    sdk.track(lambda: fake_resp, provider="anthropic", feature="chat", customer="acme")
    sdk.flush()

    assert len(cap_trans.captured) == 1
    evt = cap_trans.captured[0]
    assert evt["provider"] == "anthropic"
    assert evt["model"] == "claude-3-haiku-20240307"
    assert evt["input_tokens"] == 1000
    assert evt["output_tokens"] == 400
    assert evt["feature"] == "chat"
    assert evt["customer"] == "acme"
    assert evt["status"] == "ok"
    sdk.close()


def test_track_openai_sends_correct_event() -> None:
    """OpenAI response: prompt_tokens/completion_tokens extracted correctly."""
    cap_trans = CapturedTransport()
    sdk = _make_sdk(cap_trans.transport)
    fake_resp = _make_openai_response(
        model="gpt-4o-mini", prompt_tokens=200, completion_tokens=80
    )

    sdk.track(lambda: fake_resp, provider="openai", feature="clasificacion")
    sdk.flush()

    assert len(cap_trans.captured) == 1
    evt = cap_trans.captured[0]
    assert evt["provider"] == "openai"
    assert evt["model"] == "gpt-4o-mini"
    assert evt["input_tokens"] == 200
    assert evt["output_tokens"] == 80
    assert evt["status"] == "ok"
    assert "customer" not in evt
    sdk.close()


def test_track_uses_explicit_model_over_response_model() -> None:
    """When model is passed explicitly, it overrides the response model."""
    cap_trans = CapturedTransport()
    sdk = _make_sdk(cap_trans.transport)
    fake_resp = _make_anthropic_response(model="claude-3-5-sonnet-20241022")

    sdk.track(
        lambda: fake_resp,
        provider="anthropic",
        feature="resumen",
        model="explicit-model-override",
    )
    sdk.flush()

    evt = cap_trans.captured[0]
    assert evt["model"] == "explicit-model-override"
    sdk.close()


def test_track_records_latency_ms() -> None:
    """latency_ms must be a non-negative integer in the posted event."""
    cap_trans = CapturedTransport()
    sdk = _make_sdk(cap_trans.transport)
    fake_resp = _make_openai_response()

    sdk.track(lambda: fake_resp, provider="openai", feature="chat")
    sdk.flush()

    evt = cap_trans.captured[0]
    assert isinstance(evt["latency_ms"], int)
    assert evt["latency_ms"] >= 0
    sdk.close()


# ---------------------------------------------------------------------------
# Network failure — user never sees exception
# ---------------------------------------------------------------------------


def test_network_failure_does_not_raise_to_caller() -> None:
    """When the API is down, track() still returns the LLM response, no exception."""
    transport = make_fail_transport()
    sdk = _make_sdk(transport)
    fake_resp = _make_anthropic_response()

    result = sdk.track(lambda: fake_resp, provider="anthropic", feature="resumen")
    sdk.flush()

    assert result is fake_resp
    sdk.close()


def test_network_failure_logs_warning(caplog: pytest.LogCaptureFixture) -> None:
    """A network failure should produce a warning log, not a crash."""
    transport = make_fail_transport()
    sdk = _make_sdk(transport)
    fake_resp = _make_anthropic_response()

    with caplog.at_level(logging.WARNING, logger="tokenledger"):
        sdk.track(lambda: fake_resp, provider="anthropic", feature="resumen")
        sdk.flush()

    assert any("tokenledger" in r.name for r in caplog.records)
    sdk.close()


# ---------------------------------------------------------------------------
# LLM raises exception
# ---------------------------------------------------------------------------


def test_llm_exception_is_reraised_unchanged() -> None:
    """When fn() raises, the original exception propagates out of track()."""

    class _CustomError(RuntimeError):
        pass

    original = _CustomError("LLM call failed")
    cap_trans = CapturedTransport()
    sdk = _make_sdk(cap_trans.transport)

    with pytest.raises(_CustomError) as exc_info:
        sdk.track(
            lambda: (_ for _ in ()).throw(original),
            provider="anthropic",
            feature="chat",
            model="claude-3-haiku-20240307",
        )

    assert exc_info.value is original
    sdk.close()


def test_llm_exception_with_model_enqueues_error_event() -> None:
    """When fn() raises AND model is passed, an error event is enqueued."""
    cap_trans = CapturedTransport()
    sdk = _make_sdk(cap_trans.transport)

    try:
        sdk.track(
            lambda: 1 / 0,
            provider="anthropic",
            feature="resumen",
            model="claude-3-haiku-20240307",
        )
    except ZeroDivisionError:
        pass

    sdk.flush()

    assert len(cap_trans.captured) == 1
    evt = cap_trans.captured[0]
    assert evt["status"] == "error"
    assert evt["input_tokens"] == 0
    assert evt["output_tokens"] == 0
    assert evt["model"] == "claude-3-haiku-20240307"
    sdk.close()


def test_llm_exception_without_model_no_event_enqueued() -> None:
    """When fn() raises and model is NOT passed, no event is sent."""
    cap_trans = CapturedTransport()
    sdk = _make_sdk(cap_trans.transport)

    try:
        sdk.track(
            lambda: 1 / 0,
            provider="anthropic",
            feature="resumen",
        )
    except ZeroDivisionError:
        pass

    sdk.flush()

    assert len(cap_trans.captured) == 0
    sdk.close()


def test_llm_exception_without_model_logs_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """When fn() raises and model is NOT passed, a warning is logged."""
    cap_trans = CapturedTransport()
    sdk = _make_sdk(cap_trans.transport)

    with caplog.at_level(logging.WARNING, logger="tokenledger"):
        try:
            sdk.track(lambda: 1 / 0, provider="anthropic", feature="resumen")
        except ZeroDivisionError:
            pass

    assert any("model" in r.message.lower() for r in caplog.records)
    sdk.close()


# ---------------------------------------------------------------------------
# Missing usage in response
# ---------------------------------------------------------------------------


def test_missing_usage_skips_event(caplog: pytest.LogCaptureFixture) -> None:
    """When response has no usage, no event is sent and a warning is logged."""
    cap_trans = CapturedTransport()
    sdk = _make_sdk(cap_trans.transport)
    fake_resp = SimpleNamespace(model="claude-3-haiku-20240307")

    with caplog.at_level(logging.WARNING, logger="tokenledger"):
        result = sdk.track(lambda: fake_resp, provider="anthropic", feature="chat")
        sdk.flush()

    assert result is fake_resp
    assert len(cap_trans.captured) == 0
    assert any(
        "missing" in r.message.lower() or "skip" in r.message.lower()
        for r in caplog.records
    )
    sdk.close()


def test_missing_model_skips_event(caplog: pytest.LogCaptureFixture) -> None:
    """When response has usage but no model, and model param not passed, skip."""
    cap_trans = CapturedTransport()
    sdk = _make_sdk(cap_trans.transport)
    fake_resp = SimpleNamespace(
        usage=SimpleNamespace(input_tokens=100, output_tokens=50)
    )

    with caplog.at_level(logging.WARNING, logger="tokenledger"):
        result = sdk.track(lambda: fake_resp, provider="anthropic", feature="chat")
        sdk.flush()

    assert result is fake_resp
    assert len(cap_trans.captured) == 0
    sdk.close()


# ---------------------------------------------------------------------------
# Queue full — no blocking
# ---------------------------------------------------------------------------


def test_full_queue_drops_event_without_blocking(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """When the queue is full, _enqueue() discards the event without blocking."""
    cap_trans = CapturedTransport()
    sdk = _make_sdk(cap_trans.transport)

    # Use a small queue of size 1 and fill it
    sdk._queue = queue.Queue(maxsize=1)
    sdk._queue.put_nowait({"dummy": True})

    with caplog.at_level(logging.WARNING, logger="tokenledger"):
        start = time.perf_counter()
        sdk._enqueue({"provider": "openai", "model": "gpt-4o", "extra": "dropped"})
        elapsed = time.perf_counter() - start

    assert elapsed < 1.0, f"_enqueue blocked for {elapsed:.3f}s on a full queue"
    assert any("queue is full" in r.message.lower() for r in caplog.records)

    # Clean up the dummy item so close() flushes cleanly
    sdk._queue.get_nowait()
    sdk._queue.task_done()
    sdk.close()


# ---------------------------------------------------------------------------
# flush() delivers events
# ---------------------------------------------------------------------------


def test_flush_waits_for_events_to_be_delivered() -> None:
    """flush() should return only after all enqueued events are posted."""
    cap_trans = CapturedTransport()
    sdk = _make_sdk(cap_trans.transport)

    fake_resp = _make_anthropic_response()
    for _ in range(5):
        sdk.track(lambda: fake_resp, provider="anthropic", feature="chat")

    sdk.flush()

    assert len(cap_trans.captured) == 5
    sdk.close()


# ---------------------------------------------------------------------------
# API key never appears in logs
# ---------------------------------------------------------------------------


def test_api_key_not_in_logs(caplog: pytest.LogCaptureFixture) -> None:
    """The API key must never appear in any log record."""
    transport = make_fail_transport()
    secret_key = "super-secret-api-key-12345"
    http_client = httpx.Client(transport=transport)
    sdk = TokenLedger(
        base_url="http://test-api:8000",
        api_key=secret_key,
        timeout=1.0,
        http_client=http_client,
    )
    fake_resp = _make_anthropic_response()

    with caplog.at_level(logging.DEBUG, logger="tokenledger"):
        sdk.track(lambda: fake_resp, provider="anthropic", feature="resumen")
        sdk.flush()

    all_log_text = " ".join(r.getMessage() for r in caplog.records)
    assert secret_key not in all_log_text, (
        "API key found in log output — this is a security violation"
    )
    sdk.close()
