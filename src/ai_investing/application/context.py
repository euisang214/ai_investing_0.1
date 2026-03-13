from __future__ import annotations

import importlib
import os
from dataclasses import dataclass
from pathlib import Path

from ai_investing.config.loader import RegistryLoader
from ai_investing.config.models import AgentConfig, PanelConfig, RegistryBundle
from ai_investing.persistence.db import Database
from ai_investing.prompts.loader import PromptLoader
from ai_investing.providers.anthropic_provider import AnthropicModelProvider
from ai_investing.providers.base import ModelProvider
from ai_investing.providers.fake import FakeModelProvider
from ai_investing.providers.openai_provider import OpenAIModelProvider
from ai_investing.settings import Settings
from ai_investing.tools.registry import ToolRegistryService


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
        profile = self.registries.model_profiles.model_profiles[profile_name]
        provider_order = self._provider_order(profile_name)
        explicit_selection = self.settings.provider != "auto"
        for provider_name in provider_order:
            if provider_name == "fake":
                return FakeModelProvider()
            env_key = profile.env_model_keys.get(provider_name)
            if env_key is None:
                if explicit_selection:
                    raise RuntimeError(
                        f"Provider {provider_name} is not configured for profile {profile_name}."
                    )
                continue
            model_name = os.getenv(env_key)
            if not model_name:
                if explicit_selection:
                    raise RuntimeError(
                        f"Provider {provider_name} requires env var {env_key} "
                        f"for profile {profile_name}."
                    )
                continue
            if provider_name == "openai":
                self._require_dependency(
                    module_name="langchain_openai",
                    install_hint="Install ai-investing[openai] to use the OpenAI provider.",
                )
                return OpenAIModelProvider(model_name, profile.temperature, profile.max_tokens)
            if provider_name == "anthropic":
                self._require_dependency(
                    module_name="langchain_anthropic",
                    install_hint="Install ai-investing[anthropic] to use the Anthropic provider.",
                )
                return AnthropicModelProvider(model_name, profile.temperature, profile.max_tokens)
            if explicit_selection:
                raise RuntimeError(f"Unsupported provider requested: {provider_name}")
        return FakeModelProvider()

    @property
    def agents_config_path(self) -> Path:
        return self.settings.config_dir / "agents.yaml"

    def _provider_order(self, profile_name: str) -> list[str]:
        profile = self.registries.model_profiles.model_profiles[profile_name]
        if self.settings.provider == "auto":
            primary = profile.primary_provider
            return [
                primary,
                *[provider for provider in profile.provider_order if provider != primary],
            ]
        if self.settings.provider not in {"fake", "openai", "anthropic"}:
            raise RuntimeError(f"Unsupported provider requested: {self.settings.provider}")
        return [self.settings.provider]

    def _require_dependency(self, *, module_name: str, install_hint: str) -> None:
        try:
            importlib.import_module(module_name)
        except ImportError as exc:
            raise RuntimeError(install_hint) from exc
