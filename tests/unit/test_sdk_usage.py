import logging
from collections.abc import Generator
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest

from sdk.tokenledger import TokenLedger

SENTINEL = "sk-test-SENTINEL-123"
FIELDS = {
    "anthropic": ("input_tokens", "output_tokens"),
    "openai": ("prompt_tokens", "completion_tokens"),
}
INVALID_TOKENS = [None, -1, "100", 1.5, True, object()]
MISSING = object()


@pytest.fixture
def tracking(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[tuple[TokenLedger, MagicMock], None, None]:
    transport = httpx.MockTransport(lambda request: httpx.Response(201))
    with httpx.Client(transport=transport) as client:
        sdk = TokenLedger("http://test-api", SENTINEL, http_client=client)
        enqueue = MagicMock(wraps=sdk._enqueue)
        monkeypatch.setattr(sdk, "_enqueue", enqueue)
        try:
            yield sdk, enqueue
        finally:
            sdk.flush()
            sdk.close()


@pytest.mark.parametrize("provider", FIELDS)
@pytest.mark.parametrize("token_index", [0, 1])
@pytest.mark.parametrize(
    "value",
    INVALID_TOKENS,
    ids=["none", "negative", "string", "float", "bool", "object"],
)
def test_invalid_tokens_skip_event_without_raising(
    tracking: tuple[TokenLedger, MagicMock],
    provider: str,
    token_index: int,
    value: Any,
    caplog: pytest.LogCaptureFixture,
) -> None:
    sdk, enqueue = tracking
    fields = FIELDS[provider]
    usage = dict.fromkeys(fields, 1)
    usage[fields[token_index]] = value
    response = SimpleNamespace(model=SENTINEL, usage=SimpleNamespace(**usage))
    with caplog.at_level(logging.WARNING, logger="tokenledger"):
        assert sdk.track(lambda: response, provider, "test") is response
        sdk.flush()
    enqueue.assert_not_called()
    assert caplog.records
    assert SENTINEL not in caplog.text


@pytest.mark.parametrize("provider", FIELDS)
@pytest.mark.parametrize(
    "usage",
    [*INVALID_TOKENS, MISSING],
    ids=["none", "negative", "string", "float", "bool", "object", "missing"],
)
def test_invalid_or_missing_usage_skips_event(
    tracking: tuple[TokenLedger, MagicMock],
    provider: str,
    usage: Any,
    caplog: pytest.LogCaptureFixture,
) -> None:
    sdk, enqueue = tracking
    response = SimpleNamespace(model=SENTINEL)
    if usage is not MISSING:
        response.usage = usage
    with caplog.at_level(logging.WARNING, logger="tokenledger"):
        assert sdk.track(lambda: response, provider, "test") is response
        sdk.flush()
    enqueue.assert_not_called()
    assert caplog.records
    assert SENTINEL not in caplog.text


@pytest.mark.parametrize("provider", FIELDS)
def test_zero_integer_tokens_are_valid(
    tracking: tuple[TokenLedger, MagicMock], provider: str
) -> None:
    sdk, enqueue = tracking
    response = SimpleNamespace(
        model="test-model", usage=SimpleNamespace(**dict.fromkeys(FIELDS[provider], 0))
    )
    assert sdk.track(lambda: response, provider, "test") is response
    sdk.flush()
    enqueue.assert_called_once()


@pytest.mark.parametrize("llm_fails", [False, True])
def test_tracking_failure_never_masks_llm_result_or_exception(
    tracking: tuple[TokenLedger, MagicMock],
    llm_fails: bool,
    caplog: pytest.LogCaptureFixture,
) -> None:
    sdk, enqueue = tracking
    enqueue.side_effect = RuntimeError(SENTINEL)
    original = RuntimeError("original LLM failure")
    response = SimpleNamespace(
        model="test-model", usage=SimpleNamespace(input_tokens=1, output_tokens=1)
    )

    def call() -> SimpleNamespace:
        if llm_fails:
            raise original
        return response

    with caplog.at_level(logging.WARNING, logger="tokenledger"):
        if llm_fails:
            with pytest.raises(RuntimeError) as exc_info:
                sdk.track(call, "anthropic", "test", model="test-model")
            assert exc_info.value is original
        else:
            assert sdk.track(call, "anthropic", "test") is response
    assert caplog.records
    assert SENTINEL not in caplog.text
