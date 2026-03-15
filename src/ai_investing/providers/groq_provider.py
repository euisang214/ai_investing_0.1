from __future__ import annotations

import json

from ai_investing.domain.models import StructuredGenerationRequest
from ai_investing.providers.base import ModelProvider, ModelT


class GroqModelProvider(ModelProvider):
    def __init__(self, model_name: str, temperature: float, max_tokens: int) -> None:
        self._model_name = model_name
        self._temperature = temperature
        self._max_tokens = max_tokens

    def generate_structured(
        self, request: StructuredGenerationRequest, response_model: type[ModelT]
    ) -> ModelT:
        try:
            from langchain_groq import ChatGroq
        except ImportError as exc:  # pragma: no cover - optional dependency path
            raise RuntimeError(
                "Install ai-investing[groq] to use the Groq provider."
            ) from exc

        model = ChatGroq(
            model=self._model_name,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
        )
        runnable = model.with_structured_output(response_model)
        return runnable.invoke(
            [
                ("system", request.prompt),
                ("human", json.dumps(request.input_data, default=str, indent=2)),
            ]
        )
