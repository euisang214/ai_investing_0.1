from __future__ import annotations

import importlib
import logging
import os
from dataclasses import dataclass
from pathlib import Path

from ai_investing.config.loader import RegistryLoader
from ai_investing.config.models import AgentConfig, PanelConfig, ProviderChainEntry, RegistryBundle
from ai_investing.persistence.db import Database
from ai_investing.prompts.loader import PromptLoader
from ai_investing.providers.base import ModelProvider
from ai_investing.providers.fake import FakeModelProvider
from ai_investing.providers.openai_provider import OpenAIModelProvider
from ai_investing.settings import Settings
from ai_investing.tools.registry import ToolRegistryService

logger = logging.getLogger(__name__)


@dataclass
class AppContext:
    settings: Settings
    registries: RegistryBundle
    database: Database
    prompt_loader: PromptLoader
    tool_registry: ToolRegistryService

    @classmethod
    def load(cls, settings: Settings | None = None) -> AppContext:
        resolved_settings = settings or Settings()
        registries = RegistryLoader(
            resolved_settings.config_dir,
            prompts_dir=resolved_settings.prompts_dir,
        ).load_all()
        database = Database(resolved_settings.database_url)
        prompt_loader = PromptLoader(resolved_settings.prompts_dir)
        tool_registry = ToolRegistryService(registries)
        return cls(
            settings=resolved_settings,
            registries=registries,
            database=database,
            prompt_loader=prompt_loader,
            tool_registry=tool_registry,
        )

    def reload_registries(self) -> None:
        self.registries = RegistryLoader(
            self.settings.config_dir,
            prompts_dir=self.settings.prompts_dir,
        ).load_all()
        self.tool_registry = ToolRegistryService(self.registries)

    def get_panel(self, panel_id: str) -> PanelConfig:
        for panel in self.registries.panels.panels:
            if panel.id == panel_id:
                return panel
        raise KeyError(panel_id)

    def get_factor_name(self, factor_id: str) -> str:
        for factor in self.registries.factors.factors:
            if factor.id == factor_id:
                return factor.name
        raise KeyError(factor_id)

    def resolve_factor_name(self, factor_id: str) -> str:
        try:
            return self.get_factor_name(factor_id)
        except KeyError:
            return factor_id

    def active_agents_for_panel(self, panel_id: str) -> list[AgentConfig]:
        return [
            agent
            for agent in self.registries.agents.agents
            if agent.panel_id == panel_id and agent.enabled
        ]

    def memo_section_labels(self, label_profile: str = "default") -> dict[str, str]:
        labels: dict[str, str] = {}
        for section in sorted(
            self.registries.memo_sections.memo_sections, key=lambda item: item.order
        ):
            if not section.enabled:
                continue
            label = section.display_label
            if label_profile == "sustainability" and section.alternate_display_label:
                label = section.alternate_display_label
            labels[section.id] = label
        return labels

    def resolve_memo_section_label(
        self,
        section_id: str,
        *,
        label_profile: str = "default",
    ) -> str:
        return self.memo_section_labels(label_profile).get(section_id, section_id)

    def get_provider(self, profile_name: str) -> ModelProvider:
        """Resolve a model provider from the profile's provider chain.

        Iterates the chain entries in order. For each entry:
        - fake: returned if allow_fake_fallback is True, skipped otherwise
        - real providers: returned if the required API key env var is set,
          skipped otherwise.

        If AI_INVESTING_PROVIDER is set to a specific provider (not 'auto'),
        only that provider is considered from the chain.

        Raises RuntimeError if no valid provider is found.
        """
        profile = self.registries.model_profiles.model_profiles[profile_name]
        chain = profile.provider_chain
        explicit_provider = (
            self.settings.provider
            if self.settings.provider not in {"auto", ""}
            else None
        )

        skip_reasons: list[str] = []

        for entry in chain:
            # If user explicitly selected a provider, skip non-matching entries.
            if explicit_provider and entry.provider != explicit_provider:
                continue

            provider = self._resolve_chain_entry(
                entry, profile.temperature, profile.max_tokens, skip_reasons
            )
            if provider is not None:
                return provider

        # All entries exhausted.
        reasons = "; ".join(skip_reasons) if skip_reasons else "no entries in chain"
        raise RuntimeError(
            f"No valid provider found for profile '{profile_name}'. "
            f"Tried: {reasons}"
        )

    def _resolve_chain_entry(
        self,
        entry: ProviderChainEntry,
        temperature: float,
        max_tokens: int,
        skip_reasons: list[str],
    ) -> ModelProvider | None:
        """Try to instantiate a provider from a single chain entry.

        Returns the provider if successful, None if the entry should be skipped.
        Appends skip reasons to the list.
        """
        if entry.provider == "fake":
            if not self.settings.allow_fake_fallback:
                skip_reasons.append(
                    "fake (blocked by AI_INVESTING_ALLOW_FAKE_FALLBACK=false)"
                )
                return None
            return FakeModelProvider()

        # Check API key.
        api_key_env = entry.api_key_env
        if api_key_env:
            api_key = os.getenv(api_key_env, "")
            if not api_key:
                skip_reasons.append(
                    f"{entry.provider} (missing env var {api_key_env})"
                )
                return None

        model_name = entry.model
        return self._instantiate_provider(
            entry.provider, model_name, temperature, max_tokens
        )

    def _instantiate_provider(
        self,
        provider_name: str,
        model_name: str,
        temperature: float,
        max_tokens: int,
    ) -> ModelProvider:
        """Create a provider instance by name."""
        if provider_name == "openai":
            self._require_dependency(
                module_name="langchain_openai",
                install_hint="Install ai-investing[openai] to use the OpenAI provider.",
            )
            return OpenAIModelProvider(model_name, temperature, max_tokens)

        if provider_name == "anthropic":
            self._require_dependency(
                module_name="langchain_anthropic",
                install_hint="Install ai-investing[anthropic] to use the Anthropic provider.",
            )
            from ai_investing.providers.anthropic_provider import AnthropicModelProvider

            return AnthropicModelProvider(model_name, temperature, max_tokens)

        if provider_name == "google":
            self._require_dependency(
                module_name="langchain_google_genai",
                install_hint="Install ai-investing[google] to use the Google Gemini provider.",
            )
            from ai_investing.providers.gemini_provider import GeminiModelProvider

            return GeminiModelProvider(model_name, temperature, max_tokens)

        if provider_name == "groq":
            self._require_dependency(
                module_name="langchain_groq",
                install_hint="Install ai-investing[groq] to use the Groq provider.",
            )
            from ai_investing.providers.groq_provider import GroqModelProvider

            return GroqModelProvider(model_name, temperature, max_tokens)

        if provider_name == "openai_compatible":
            self._require_dependency(
                module_name="langchain_openai",
                install_hint=(
                    "Install ai-investing[openai] to use the OpenAI-compatible provider."
                ),
            )
            base_url = os.getenv("OPENAI_COMPATIBLE_BASE_URL", "")
            if not base_url:
                raise RuntimeError(
                    "OPENAI_COMPATIBLE_BASE_URL must be set to use the openai_compatible provider."
                )
            from ai_investing.providers.openai_compatible_provider import (
                OpenAICompatibleModelProvider,
            )

            return OpenAICompatibleModelProvider(
                model_name, temperature, max_tokens, base_url
            )

        raise RuntimeError(f"Unsupported provider: {provider_name}")

    @property
    def agents_config_path(self) -> Path:
        return self.settings.config_dir / "agents.yaml"

    def _require_dependency(self, *, module_name: str, install_hint: str) -> None:
        try:
            importlib.import_module(module_name)
        except ImportError as exc:
            raise RuntimeError(install_hint) from exc
