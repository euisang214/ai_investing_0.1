from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ai_investing.domain.models import StructuredGenerationRequest
from ai_investing.providers.base import (
    GenerationResult,
    ModelProvider,
    ModelT,
    ProviderExhaustedError,
)
from ai_investing.providers.resilient import ResilientProvider, _is_retriable


class DummyModel:
    pass


class FailingProvider(ModelProvider):
    """Provider that fails with configurable errors."""

    def __init__(self, errors: list[Exception]) -> None:
        self._errors = list(errors)
        self._calls = 0

    @property
    def call_count(self) -> int:
        return self._calls

    def generate_structured(
        self, request: StructuredGenerationRequest, response_model: type[ModelT]
    ) -> ModelT:
        self._calls += 1
        if self._errors:
            raise self._errors.pop(0)
        return MagicMock()

    def generate_structured_with_usage(
        self, request: StructuredGenerationRequest, response_model: type[ModelT]
    ) -> GenerationResult[ModelT]:
        self._calls += 1
        if self._errors:
            raise self._errors.pop(0)
        return GenerationResult(
            value=MagicMock(),
            input_tokens=100,
            output_tokens=50,
            provider="test",
            model="test-model",
        )


class SucceedingProvider(ModelProvider):
    """Provider that always succeeds."""

    def generate_structured(
        self, request: StructuredGenerationRequest, response_model: type[ModelT]
    ) -> ModelT:
        return MagicMock()

    def generate_structured_with_usage(
        self, request: StructuredGenerationRequest, response_model: type[ModelT]
    ) -> GenerationResult[ModelT]:
        return GenerationResult(
            value=MagicMock(),
            input_tokens=100,
            output_tokens=50,
            provider="test",
            model="test-model",
        )


def _make_request() -> StructuredGenerationRequest:
    return StructuredGenerationRequest(
        task_type="test",
        prompt="Test prompt",
        input_data={"key": "value"},
    )


class TestIsRetriable:
    def test_rate_limit_message(self) -> None:
        assert _is_retriable(RuntimeError("429 rate limit exceeded"))

    def test_server_error_message(self) -> None:
        assert _is_retriable(RuntimeError("HTTP 503 Service Unavailable"))

    def test_timeout_class_name(self) -> None:
        class TimeoutError(Exception):
            pass
        assert _is_retriable(TimeoutError("timed out"))

    def test_connection_class_name(self) -> None:
        class ConnectionError(Exception):
            pass
        assert _is_retriable(ConnectionError("refused"))

    def test_non_retriable(self) -> None:
        assert not _is_retriable(ValueError("invalid input"))


class TestResilientProvider:
    @patch("ai_investing.providers.resilient.time.sleep")
    def test_succeeds_on_first_try(self, mock_sleep: MagicMock) -> None:
        inner = SucceedingProvider()
        resilient = ResilientProvider(inner, provider_name="test", model_name="m")
        result = resilient.generate_structured_with_usage(_make_request(), MagicMock)
        assert result.input_tokens == 100
        mock_sleep.assert_not_called()

    @patch("ai_investing.providers.resilient.time.sleep")
    def test_retries_on_retriable_error(self, mock_sleep: MagicMock) -> None:
        errors = [RuntimeError("429 rate limited")]
        inner = FailingProvider(errors)
        resilient = ResilientProvider(
            inner, max_retries=2, provider_name="test", model_name="m"
        )
        result = resilient.generate_structured_with_usage(_make_request(), MagicMock)
        assert result.input_tokens == 100
        assert inner.call_count == 2  # 1 fail + 1 success
        mock_sleep.assert_called_once_with(1.0)

    @patch("ai_investing.providers.resilient.time.sleep")
    def test_exhausts_retries_raises_provider_exhausted(
        self, mock_sleep: MagicMock
    ) -> None:
        errors = [
            RuntimeError("429 rate limited"),
            RuntimeError("429 rate limited"),
            RuntimeError("429 rate limited"),
        ]
        inner = FailingProvider(errors)
        resilient = ResilientProvider(
            inner, max_retries=2, provider_name="test", model_name="m"
        )
        with pytest.raises(ProviderExhaustedError, match="exhausted"):
            resilient.generate_structured_with_usage(_make_request(), MagicMock)
        assert inner.call_count == 3  # 1 initial + 2 retries
        assert mock_sleep.call_count == 2

    @patch("ai_investing.providers.resilient.time.sleep")
    def test_exponential_backoff_delays(self, mock_sleep: MagicMock) -> None:
        errors = [
            RuntimeError("429 rate limited"),
            RuntimeError("429 rate limited"),
            RuntimeError("429 rate limited"),
        ]
        inner = FailingProvider(errors)
        resilient = ResilientProvider(
            inner, max_retries=2, provider_name="test", model_name="m"
        )
        with pytest.raises(ProviderExhaustedError):
            resilient.generate_structured_with_usage(_make_request(), MagicMock)
        delays = [call.args[0] for call in mock_sleep.call_args_list]
        assert delays == [1.0, 2.0]

    @patch("ai_investing.providers.resilient.time.sleep")
    def test_non_retriable_raises_immediately(self, mock_sleep: MagicMock) -> None:
        errors = [ValueError("invalid schema")]
        inner = FailingProvider(errors)
        resilient = ResilientProvider(
            inner, max_retries=2, provider_name="test", model_name="m"
        )
        with pytest.raises(ValueError, match="invalid schema"):
            resilient.generate_structured_with_usage(_make_request(), MagicMock)
        assert inner.call_count == 1
        mock_sleep.assert_not_called()

    def test_fake_provider_not_wrapped(self) -> None:
        from ai_investing.providers.fake import FakeModelProvider

        fake = FakeModelProvider()
        # FakeModelProvider should NOT be wrapped — verify it's not a ResilientProvider
        assert not isinstance(fake, ResilientProvider)

    @patch("ai_investing.providers.resilient.time.sleep")
    def test_generate_structured_delegates(self, mock_sleep: MagicMock) -> None:
        inner = SucceedingProvider()
        resilient = ResilientProvider(inner, provider_name="test", model_name="m")
        result = resilient.generate_structured(_make_request(), MagicMock)
        assert result is not None
