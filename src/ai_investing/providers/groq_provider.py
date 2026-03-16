from __future__ import annotations

import json

from ai_investing.domain.models import StructuredGenerationRequest
from ai_investing.providers.base import GenerationResult, ModelProvider, ModelT


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

    def generate_structured_with_usage(
        self, request: StructuredGenerationRequest, response_model: type[ModelT]
    ) -> GenerationResult[ModelT]:
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
        runnable = model.with_structured_output(response_model, include_raw=True)
        response = runnable.invoke(
            [
                ("system", request.prompt),
                ("human", json.dumps(request.input_data, default=str, indent=2)),
            ]
        )
        parsed = response.get("parsed")
        if parsed is None:
            raise ValueError(f"Failed to generate structured output: {response}")
        raw = response.get("raw")
        usage = getattr(raw, "response_metadata", {}).get("token_usage", {})
        input_tokens = getattr(usage, "prompt_tokens", usage.get("prompt_tokens", 0)) if hasattr(usage, "prompt_tokens") or isinstance(usage, dict) else 0
        output_tokens = getattr(usage, "completion_tokens", usage.get("completion_tokens", 0)) if hasattr(usage, "completion_tokens") or isinstance(usage, dict) else 0

        return GenerationResult(
            value=parsed,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            provider="groq",
            model=self._model_name,
        )
