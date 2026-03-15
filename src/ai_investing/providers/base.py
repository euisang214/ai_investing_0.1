from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar

from pydantic import BaseModel

from ai_investing.domain.models import StructuredGenerationRequest

ModelT = TypeVar("ModelT", bound=BaseModel)


@dataclass
class GenerationResult(Generic[ModelT]):
    """Result of a structured LLM generation including token usage."""

    value: ModelT
    input_tokens: int
    output_tokens: int
    provider: str
    model: str


class ProviderExhaustedError(RuntimeError):
    """Raised when all retry attempts for a provider are exhausted."""


class ModelProvider(ABC):
    @abstractmethod
    def generate_structured(
        self, request: StructuredGenerationRequest, response_model: type[ModelT]
    ) -> ModelT:
        raise NotImplementedError

    def generate_structured_with_usage(
        self, request: StructuredGenerationRequest, response_model: type[ModelT]
    ) -> GenerationResult[ModelT]:
        """Generate structured output with token usage metadata.

        Default implementation calls generate_structured and returns zero
        token counts. Real providers should override to extract actual
        token usage from the LLM response.
        """
        value = self.generate_structured(request, response_model)
        return GenerationResult(
            value=value,
            input_tokens=0,
            output_tokens=0,
            provider="unknown",
            model="unknown",
        )
