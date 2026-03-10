from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel

from ai_investing.domain.models import StructuredGenerationRequest

ModelT = TypeVar("ModelT", bound=BaseModel)


class ModelProvider(ABC):
    @abstractmethod
    def generate_structured(
        self, request: StructuredGenerationRequest, response_model: type[ModelT]
    ) -> ModelT:
        raise NotImplementedError
