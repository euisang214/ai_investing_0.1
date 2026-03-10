from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SUPPORTED_OUTPUT_SCHEMAS = frozenset(
    {
        "ClaimCard",
        "PanelVerdict",
        "GatekeeperVerdict",
        "MemoSectionUpdate",
        "ICMemo",
        "MonitoringDelta",
    }
)
SUPPORTED_PANEL_SUBGRAPHS = frozenset({"gatekeeper", "debate"})
INTERNAL_AGENT_PANEL_IDS = frozenset({"memo_updates", "ic", "monitoring"})


class ConfigModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PanelConfig(ConfigModel):
    id: str
    name: str
    enabled: bool
    scope: Literal["public", "private", "both"]
    implemented: bool
    subgraph: str
    output_schema: str
    prompt_path: str
    memo_section_ids: list[str]
    factor_ids: list[str] = Field(default_factory=list)


class PanelsRegistry(ConfigModel):
    panels: list[PanelConfig]


class FactorConfig(ConfigModel):
    id: str
    panel_id: str
    name: str
    description: str
    implemented: bool


class FactorsRegistry(ConfigModel):
    factors: list[FactorConfig]


class MemoSectionConfig(ConfigModel):
    id: str
    display_label: str
    order: int
    enabled: bool
    alternate_display_label: str | None = None


class MemoSectionsRegistry(ConfigModel):
    memo_sections: list[MemoSectionConfig]


class AgentConfig(ConfigModel):
    id: str
    name: str
    panel_id: str
    parent_id: str | None = None
    role_type: str
    goal: str
    enabled: bool
    prompt_path: str
    input_channels: list[str]
    output_schema: str
    memory_read_namespaces: list[str]
    memory_write_namespaces: list[str]
    allowed_tool_bundle: str
    model_profile: str
    scope: Literal["public", "private", "both"]
    tags: list[str] = Field(default_factory=list)


class AgentsRegistry(ConfigModel):
    agents: list[AgentConfig]


class ModelProfileConfig(ConfigModel):
    primary_provider: str
    provider_order: list[str]
    env_model_keys: dict[str, str]
    temperature: float
    max_tokens: int

    @model_validator(mode="after")
    def validate_provider_order(self) -> ModelProfileConfig:
        if self.primary_provider not in self.provider_order:
            raise ValueError("primary_provider must be included in provider_order")
        unknown_env_keys = set(self.env_model_keys) - set(self.provider_order)
        if unknown_env_keys:
            joined = ", ".join(sorted(unknown_env_keys))
            raise ValueError(f"env_model_keys reference providers outside provider_order: {joined}")
        return self


class ModelProfilesRegistry(ConfigModel):
    model_profiles: dict[str, ModelProfileConfig]


class ToolDefinition(ConfigModel):
    id: str
    category: str
    kind: str
    description: str
    handler: str


class ToolRegistry(ConfigModel):
    tools: list[ToolDefinition]


class ToolBundle(ConfigModel):
    id: str
    tool_ids: list[str]


class ToolBundlesRegistry(ConfigModel):
    bundles: list[ToolBundle]


class SourceConnectorConfig(ConfigModel):
    id: str
    company_type: Literal["public", "private", "both"]
    kind: str
    manifest_file: str
    raw_landing_zone: str


class SourceConnectorsRegistry(ConfigModel):
    connectors: list[SourceConnectorConfig]


class MonitoringConfig(ConfigModel):
    delta_thresholds: dict[str, Any]
    drift_flags: list[str]
    alert_levels: dict[str, str]


class MonitoringRegistry(ConfigModel):
    monitoring: MonitoringConfig


class RunPolicyConfig(ConfigModel):
    cadence: str
    default_panel_ids: list[str]
    memo_reconciliation: bool
    monitoring_enabled: bool
    allow_unimplemented_panels: bool = False


class RunPoliciesRegistry(ConfigModel):
    run_policies: dict[str, RunPolicyConfig]


class RegistryBundle(ConfigModel):
    panels: PanelsRegistry
    factors: FactorsRegistry
    memo_sections: MemoSectionsRegistry
    agents: AgentsRegistry
    model_profiles: ModelProfilesRegistry
    tool_registry: ToolRegistry
    tool_bundles: ToolBundlesRegistry
    source_connectors: SourceConnectorsRegistry
    monitoring: MonitoringRegistry
    run_policies: RunPoliciesRegistry
