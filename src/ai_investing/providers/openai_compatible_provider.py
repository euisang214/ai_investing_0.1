from __future__ import annotations

import json
import os

from ai_investing.domain.models import StructuredGenerationRequest
from ai_investing.providers.base import GenerationResult, ModelProvider, ModelT


class OpenAICompatibleModelProvider(ModelProvider):
    """Provider adapter for any OpenAI-compatible API endpoint."""

    def __init__(
        self,
        model_name: str,
        temperature: float,
        max_tokens: int,
        base_url: str,
    ) -> None:
        self._model_name = model_name
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._base_url = base_url

    def generate_structured(
        self, request: StructuredGenerationRequest, response_model: type[ModelT]
    ) -> ModelT:
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:  # pragma: no cover - optional dependency path
            raise RuntimeError(
                "Install ai-investing[openai] to use the OpenAI-compatible provider."
            ) from exc

        api_key = os.getenv("OPENAI_COMPATIBLE_API_KEY", "")
        model = ChatOpenAI(
            model=self._model_name,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
            base_url=self._base_url,
            api_key=api_key,
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
            from langchain_openai import ChatOpenAI
        except ImportError as exc:  # pragma: no cover - optional dependency path
            raise RuntimeError(
                "Install ai-investing[openai] to use the OpenAI-compatible provider."
            ) from exc

        api_key = os.getenv("OPENAI_COMPATIBLE_API_KEY", "")
        model = ChatOpenAI(
            model=self._model_name,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
            base_url=self._base_url,
            api_key=api_key,
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
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        return GenerationResult(
            value=parsed,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            provider="openai_compatible",
            model=self._model_name,
        )
