from __future__ import annotations

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
    def load(cls, settings: Settings | None = None) -> "AppContext":
        resolved_settings = settings or Settings()
        registries = RegistryLoader(resolved_settings.config_dir).load_all()
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
        self.registries = RegistryLoader(self.settings.config_dir).load_all()
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

    def get_provider(self, profile_name: str) -> ModelProvider:
        profile = self.registries.model_profiles.model_profiles[profile_name]
        provider_order = [self.settings.provider] if self.settings.provider != "auto" else profile.provider_order
        for provider_name in provider_order:
            if provider_name == "fake":
                return FakeModelProvider()
            env_key = profile.env_model_keys.get(provider_name)
            if env_key is None:
                continue
            model_name = os.getenv(env_key)
            if not model_name:
                continue
            if provider_name == "openai":
                return OpenAIModelProvider(model_name, profile.temperature, profile.max_tokens)
            if provider_name == "anthropic":
                return AnthropicModelProvider(model_name, profile.temperature, profile.max_tokens)
        return FakeModelProvider()

    @property
    def agents_config_path(self) -> Path:
        return self.settings.config_dir / "agents.yaml"

