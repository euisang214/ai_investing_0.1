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
SUPPORTED_SOURCE_CONNECTOR_KINDS = frozenset({"file_bundle", "mcp_stub"})
SUPPORTED_CADENCE_POLICY_KINDS = frozenset(
    {"weekly", "biweekly", "weekdays", "monthly", "custom_weekdays"}
)
SUPPORTED_WEEKDAY_VALUES = frozenset(
    {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
)


class ConfigModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OpenConfigModel(BaseModel):
    model_config = ConfigDict(extra="allow")


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


class SourceConnectorSettings(BaseModel):
    model_config = ConfigDict(extra="allow")

    manifest_file: str | None = None
    raw_landing_zone: str | None = None


class SourceConnectorLiveRefresh(ConfigModel):
    posture: Literal["static", "manual", "scheduled"] = "static"
    cadence: str | None = None
    max_staleness_hours: int | None = None


class SourceConnectorEvidencePolicy(ConfigModel):
    extraction_mode: Literal["full_text", "metadata_only", "attachment_only"] = "full_text"
    attachment_handling: Literal["copy_to_raw", "reference_only"] = "copy_to_raw"


class SourceConnectorConfig(ConfigModel):
    id: str
    company_type: Literal["public", "private", "both"]
    kind: str
    manifest_file: str = ""
    raw_landing_zone: str = ""
    settings: SourceConnectorSettings = Field(default_factory=SourceConnectorSettings)
    live_refresh: SourceConnectorLiveRefresh = Field(default_factory=SourceConnectorLiveRefresh)
    evidence_policy: SourceConnectorEvidencePolicy = Field(
        default_factory=SourceConnectorEvidencePolicy
    )
    capabilities: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_settings(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        payload = dict(data)
        raw_settings = payload.get("settings")
        if raw_settings is None:
            settings: dict[str, Any] = {}
        elif isinstance(raw_settings, dict):
            settings = dict(raw_settings)
        else:
            raise ValueError("settings must be a mapping")

        for field_name in ("manifest_file", "raw_landing_zone"):
            raw_value = payload.get(field_name)
            if raw_value not in (None, ""):
                if field_name in settings and settings[field_name] != raw_value:
                    raise ValueError(
                        f"{field_name} must match the explicit settings value when both are set"
                    )
                settings.setdefault(field_name, raw_value)

        payload["settings"] = settings
        return payload

    @model_validator(mode="after")
    def sync_compatibility_fields(self) -> SourceConnectorConfig:
        manifest_file = self.settings.manifest_file or self.manifest_file
        raw_landing_zone = self.settings.raw_landing_zone or self.raw_landing_zone
        self.settings.manifest_file = manifest_file
        self.settings.raw_landing_zone = raw_landing_zone
        self.manifest_file = manifest_file or ""
        self.raw_landing_zone = raw_landing_zone or ""
        self.capabilities = list(
            dict.fromkeys(
                capability.strip()
                for capability in self.capabilities
                if capability and capability.strip()
            )
        )
        return self

    def setting(self, name: str) -> Any:
        if hasattr(self.settings, name):
            return getattr(self.settings, name)
        return self.settings.model_extra.get(name) if self.settings.model_extra else None

    def require_setting(self, name: str) -> str:
        value = self.setting(name)
        if value in (None, ""):
            raise ValueError(f"Connector {self.id} must declare setting '{name}'")
        return str(value)

    def supports_company_type(self, company_type: str) -> bool:
        return self.company_type == "both" or self.company_type == company_type


class SourceConnectorsRegistry(ConfigModel):
    connectors: list[SourceConnectorConfig]


class CadencePolicyConfig(OpenConfigModel):
    id: str
    label: str
    kind: str
    weekday: str | None = None
    weekdays: list[str] = Field(default_factory=list)
    day_of_month: int | None = None

    @model_validator(mode="after")
    def validate_shape(self) -> CadencePolicyConfig:
        if self.kind not in SUPPORTED_CADENCE_POLICY_KINDS:
            raise ValueError(f"Unsupported cadence policy kind: {self.kind}")

        normalized_weekday = self.weekday.strip().lower() if self.weekday else None
        normalized_weekdays = [value.strip().lower() for value in self.weekdays]
        invalid_weekdays = [
            value for value in [normalized_weekday, *normalized_weekdays] if value is not None
        ]
        invalid_weekdays = [
            value for value in invalid_weekdays if value not in SUPPORTED_WEEKDAY_VALUES
        ]
        if invalid_weekdays:
            joined = ", ".join(sorted(dict.fromkeys(invalid_weekdays)))
            raise ValueError(f"Invalid weekday values: {joined}")

        if normalized_weekday is not None:
            self.weekday = normalized_weekday
        self.weekdays = normalized_weekdays

        if self.kind in {"weekly", "biweekly"} and self.weekday is None:
            raise ValueError(f"{self.kind} cadence policies require weekday")
        if self.kind == "weekdays":
            if self.weekday is not None or self.weekdays:
                raise ValueError("weekdays cadence policies do not accept weekday overrides")
        if self.kind == "monthly":
            if self.day_of_month is None:
                raise ValueError("monthly cadence policies require day_of_month")
            if not 1 <= self.day_of_month <= 28:
                raise ValueError("day_of_month must be between 1 and 28")
            if self.weekday is not None or self.weekdays:
                raise ValueError("monthly cadence policies do not accept weekday fields")
        if self.kind == "custom_weekdays":
            if self.weekday is not None:
                raise ValueError("custom_weekdays cadence policies use weekdays, not weekday")
            if not self.weekdays:
                raise ValueError("custom_weekdays cadence policies require weekdays")
            if len(set(self.weekdays)) != len(self.weekdays):
                raise ValueError("custom_weekdays cadence policies require unique weekdays")
        if self.kind in {"weekly", "biweekly"} and self.weekdays:
            raise ValueError(f"{self.kind} cadence policies do not accept weekdays")
        return self


class CadencePoliciesRegistry(ConfigModel):
    workspace_timezone: str
    default_policy_id: str = "weekly"
    cadence_policies: list[CadencePolicyConfig]


class MonitoringDriftRule(ConfigModel):
    factor_ids: list[str]
    drift_flag: str
    label: str
    reason: str
    related_section_ids: list[str] = Field(default_factory=list)


class MonitoringContradictionConfig(ConfigModel):
    positive_markers: list[str] = Field(default_factory=list)
    negative_markers: list[str] = Field(default_factory=list)
    minimum_confidence: float = 0.45
    max_references: int = 2


class MonitoringAnalogConfig(ConfigModel):
    max_references: int = 2
    min_score: float = 1.0
    factor_overlap_weight: float = 1.0
    stance_match_weight: float = 0.6
    metric_overlap_weight: float = 0.25


class MonitoringConcentrationView(ConfigModel):
    id: str
    label: str
    factor_ids: list[str]
    metric_keys: list[str] = Field(default_factory=list)
    worsening_stances: list[str] = Field(default_factory=lambda: ["negative", "mixed"])
    stable_state: str = "stable"
    pressured_state: str = "pressured"


class MonitoringConfig(ConfigModel):
    delta_thresholds: dict[str, Any]
    drift_flags: list[str]
    alert_levels: dict[str, str]
    drift_rules: list[MonitoringDriftRule] = Field(default_factory=list)
    contradiction: MonitoringContradictionConfig = Field(
        default_factory=MonitoringContradictionConfig
    )
    analog: MonitoringAnalogConfig = Field(default_factory=MonitoringAnalogConfig)
    concentration_views: list[MonitoringConcentrationView] = Field(default_factory=list)


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
    cadence_policies: CadencePoliciesRegistry
    monitoring: MonitoringRegistry
    run_policies: RunPoliciesRegistry
