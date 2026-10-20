"""TokenLedger SDK — non-blocking LLM usage tracking client.

Usage:
    from sdk.tokenledger import TokenLedger

    tl = TokenLedger(base_url="http://localhost:8000", api_key="your-key")
    response = tl.track(
        lambda: client.messages.create(...),
        provider="anthropic",
        feature="resumen",
        customer="acme",
    )
    tl.close()
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from collections.abc import Callable
from typing import Any

import httpx


def _get_logger() -> logging.Logger:
    logger = logging.getLogger("tokenledger")
    logger.disabled = False
    return logger


# Maximum events held in the in-memory queue before discarding
_QUEUE_MAX_SIZE = 1000


def _extract_anthropic(response: Any) -> tuple[str | None, int, int]:
    """Extract model and tokens from an Anthropic-style response object."""
    try:
        model: str | None = getattr(response, "model", None)
        usage = getattr(response, "usage", None)
        if usage is None:
            return model, -1, -1
        input_tokens: int = getattr(usage, "input_tokens", -1)
        output_tokens: int = getattr(usage, "output_tokens", -1)
        return model, input_tokens, output_tokens
    except Exception:  # noqa: BLE001
        return None, -1, -1


def _extract_openai(response: Any) -> tuple[str | None, int, int]:
    """Extract model and tokens from an OpenAI-style response object."""
    try:
        model: str | None = getattr(response, "model", None)
        usage = getattr(response, "usage", None)
        if usage is None:
            return model, -1, -1
        input_tokens: int = getattr(usage, "prompt_tokens", -1)
        output_tokens: int = getattr(usage, "completion_tokens", -1)
        return model, input_tokens, output_tokens
    except Exception:  # noqa: BLE001
        return None, -1, -1


_EXTRACTORS: dict[str, Callable[[Any], tuple[str | None, int, int]]] = {
    "anthropic": _extract_anthropic,
    "openai": _extract_openai,
}


class TokenLedger:
    """Non-blocking SDK client for TokenLedger.

    Wraps an LLM call with `track()`, extracts token usage from the response,
    and posts the event asynchronously to the TokenLedger API without ever
    blocking or raising exceptions in the caller's thread.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: float = 2.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._http_client = http_client or httpx.Client(timeout=timeout)
        self._owns_http_client = http_client is None

        self._queue: queue.Queue[dict[str, Any] | None] = queue.Queue(
            maxsize=_QUEUE_MAX_SIZE
        )
        self._worker = threading.Thread(
            target=self._run_worker,
            daemon=True,
            name="tokenledger-worker",
        )
        self._worker.start()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def track(
        self,
        fn: Callable[[], Any],
        provider: str,
        feature: str,
        customer: str | None = None,
        model: str | None = None,
    ) -> Any:
        """Execute fn(), record its token usage, and return the original result.

        Never raises an exception due to TokenLedger internals. If fn() raises,
        the exception is re-raised unchanged after enqueueing an error event
        (when model is known).
        """
        start = time.perf_counter()
        exc_raised: BaseException | None = None
        response: Any = None

        try:
            response = fn()
        except BaseException as exc:  # noqa: BLE001
            exc_raised = exc

        latency_ms = int((time.perf_counter() - start) * 1000)

        if exc_raised is not None:
            # fn() raised — enqueue error event only if model is known
            if model is not None:
                self._enqueue(
                    {
                        "provider": provider,
                        "model": model,
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "feature": feature,
                        "customer": customer,
                        "latency_ms": latency_ms,
                        "status": "error",
                    }
                )
            else:
                _get_logger().warning(
                    "tokenledger: LLM call failed and model is unknown; "
                    "skipping error event"
                )
            raise exc_raised  # re-raise original, unwrapped

        # fn() succeeded — extract usage from response
        extractor = _EXTRACTORS.get(provider)
        if extractor is None:
            _get_logger().warning(
                "tokenledger: unsupported provider '%s'; skipping event", provider
            )
            return response

        resolved_model, input_tokens, output_tokens = extractor(response)

        # If model was not passed, use the one from the response
        effective_model = model or resolved_model

        if effective_model is None:
            _get_logger().warning(
                "tokenledger: could not determine model from response; skipping event"
            )
            return response

        if input_tokens < 0 or output_tokens < 0:
            _get_logger().warning(
                "tokenledger: token usage missing in response for model '%s'; "
                "skipping event",
                effective_model,
            )
            return response

        self._enqueue(
            {
                "provider": provider,
                "model": effective_model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "feature": feature,
                "customer": customer,
                "latency_ms": latency_ms,
                "status": "ok",
            }
        )
        return response

    def flush(self, timeout: float = 5.0) -> None:
        """Block until the event queue is empty or timeout elapses."""
        deadline = time.monotonic() + timeout
        with self._queue.all_tasks_done:
            while self._queue.unfinished_tasks:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                self._queue.all_tasks_done.wait(remaining)

    def close(self) -> None:
        """Flush pending events, stop the worker, and close the HTTP client."""
        self.flush()
        try:
            self._queue.put(None, block=False)
            self._worker.join(timeout=self._timeout)
        except (queue.Full, Exception):
            pass
        if self._owns_http_client:
            self._http_client.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _enqueue(self, payload: dict[str, Any]) -> None:
        """Put payload on the queue; drop with a warning if the queue is full."""
        try:
            self._queue.put_nowait(payload)
        except queue.Full:
            _get_logger().warning(
                "tokenledger: event queue is full (%d); dropping event",
                _QUEUE_MAX_SIZE,
            )

    def _run_worker(self) -> None:
        """Background daemon that drains the queue and posts events to the API."""
        while True:
            try:
                item = self._queue.get()
            except Exception:  # noqa: BLE001
                break

            try:
                if item is None:
                    # Sentinel — shut down
                    break
                self._post_event(item)
            except Exception:  # noqa: BLE001
                _get_logger().warning(
                    "tokenledger: unexpected error in worker thread",
                    exc_info=True,
                )
            finally:
                self._queue.task_done()

    def _post_event(self, payload: dict[str, Any]) -> None:
        """POST a single event payload to /v1/events. Swallows all exceptions."""
        clean_payload = {k: v for k, v in payload.items() if v is not None}
        kwargs: dict[str, Any] = {
            "json": clean_payload,
            "headers": {"X-API-Key": self._api_key},
        }
        if not type(self._http_client).__name__.endswith("TestClient"):
            kwargs["timeout"] = self._timeout

        try:
            response = self._http_client.post(
                f"{self._base_url}/v1/events",
                **kwargs,
            )
            if response.status_code not in (200, 201):
                _get_logger().warning(
                    "tokenledger: server returned %d for event (provider=%s model=%s)",
                    response.status_code,
                    payload.get("provider"),
                    payload.get("model"),
                )
        except httpx.HTTPError as exc:
            _get_logger().warning(
                "tokenledger: HTTP error posting event (provider=%s model=%s): %s",
                payload.get("provider"),
                payload.get("model"),
                type(exc).__name__,
            )
        except Exception:  # noqa: BLE001
            _get_logger().warning(
                "tokenledger: unexpected error posting event",
                exc_info=True,
            )
