"""Resilient provider wrapper with retry and exponential backoff.

Wraps any ModelProvider to add retry logic on transient errors
(429 rate limits, 5xx server errors, timeouts, network failures).
After retries are exhausted, raises ProviderExhaustedError so the
caller can fall through to the next provider in the chain.
"""

from __future__ import annotations

import time

from ai_investing.domain.models import StructuredGenerationRequest
from ai_investing.logging import get_logger
from ai_investing.providers.base import (
    GenerationResult,
    ModelProvider,
    ModelT,
    ProviderExhaustedError,
)

logger = get_logger(__name__)

# Retry delays in seconds (exponential backoff: 1s, 2s, 4s).
_RETRY_DELAYS = [1.0, 2.0, 4.0]

# Errors considered retriable.
_RETRIABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def _is_retriable(exc: Exception) -> bool:
    """Check if an exception is retriable."""
    # httpx HTTP status errors with retriable codes.
    try:
        import httpx

        if isinstance(exc, httpx.HTTPStatusError):
            return exc.response.status_code in _RETRIABLE_STATUS_CODES
        if isinstance(exc, httpx.TimeoutException | httpx.ConnectError):
            return True
    except ImportError:
        pass

    # Generic connection/timeout errors from various HTTP libs.
    error_name = type(exc).__name__.lower()
    retriable_names = {"timeout", "connect", "connectionerror", "readtimeout"}
    if any(name in error_name for name in retriable_names):
        return True

    # Check for rate limit or server errors in the message.
    msg = str(exc).lower()
    if "429" in msg or "rate limit" in msg:
        return True
    if any(f"{code}" in msg for code in (500, 502, 503, 504)):
        return True

    return False


class ResilientProvider(ModelProvider):
    """Wraps a ModelProvider with retry logic and exponential backoff."""

    def __init__(
        self,
        inner: ModelProvider,
        *,
        max_retries: int = 2,
        provider_name: str = "unknown",
        model_name: str = "unknown",
    ) -> None:
        self._inner = inner
        self._max_retries = max_retries
        self._provider_name = provider_name
        self._model_name = model_name

    def generate_structured(
        self, request: StructuredGenerationRequest, response_model: type[ModelT]
    ) -> ModelT:
        result = self.generate_structured_with_usage(request, response_model)
        return result.value

    def generate_structured_with_usage(
        self, request: StructuredGenerationRequest, response_model: type[ModelT]
    ) -> GenerationResult[ModelT]:
        last_error: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                return self._inner.generate_structured_with_usage(
                    request, response_model
                )
            except Exception as exc:
                last_error = exc
                if not _is_retriable(exc):
                    raise

                if attempt < self._max_retries:
                    delay = _RETRY_DELAYS[min(attempt, len(_RETRY_DELAYS) - 1)]
                    logger.warning(
                        "provider_retry",
                        provider=self._provider_name,
                        model=self._model_name,
                        attempt=attempt + 1,
                        max_retries=self._max_retries,
                        delay_seconds=delay,
                        error_type=type(exc).__name__,
                        error=str(exc)[:200],
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        "provider_exhausted",
                        provider=self._provider_name,
                        model=self._model_name,
                        attempts=self._max_retries + 1,
                        error_type=type(exc).__name__,
                        error=str(exc)[:200],
                    )

        raise ProviderExhaustedError(
            f"Provider {self._provider_name} ({self._model_name}) exhausted "
            f"after {self._max_retries + 1} attempts: {last_error}"
        )
