from __future__ import annotations

from pathlib import Path
from typing import TypeVar

import yaml

from ai_investing.config.models import (
    INTERNAL_AGENT_PANEL_IDS,
    SUPPORTED_OUTPUT_SCHEMAS,
    SUPPORTED_PANEL_SUBGRAPHS,
    AgentsRegistry,
    FactorsRegistry,
    MemoSectionsRegistry,
    ModelProfilesRegistry,
    MonitoringRegistry,
    PanelsRegistry,
    RegistryBundle,
    RunPoliciesRegistry,
    SourceConnectorsRegistry,
    ToolBundlesRegistry,
    ToolRegistry,
)

ConfigT = TypeVar("ConfigT")


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected a mapping in {path}")
    return data


def load_typed_yaml(path: Path, model_type: type[ConfigT]) -> ConfigT:
    return model_type.model_validate(load_yaml(path))


class RegistryLoader:
    def __init__(self, config_dir: Path, prompts_dir: Path | None = None):
        self._config_dir = config_dir
        self._prompts_dir = prompts_dir

    def load_all(self) -> RegistryBundle:
        bundle = RegistryBundle(
            panels=load_typed_yaml(self._config_dir / "panels.yaml", PanelsRegistry),
            factors=load_typed_yaml(self._config_dir / "factors.yaml", FactorsRegistry),
            memo_sections=load_typed_yaml(
                self._config_dir / "memo_sections.yaml", MemoSectionsRegistry
            ),
            agents=load_typed_yaml(self._config_dir / "agents.yaml", AgentsRegistry),
            model_profiles=load_typed_yaml(
                self._config_dir / "model_profiles.yaml", ModelProfilesRegistry
            ),
            tool_registry=load_typed_yaml(self._config_dir / "tool_registry.yaml", ToolRegistry),
            tool_bundles=load_typed_yaml(
                self._config_dir / "tool_bundles.yaml", ToolBundlesRegistry
            ),
            source_connectors=load_typed_yaml(
                self._config_dir / "source_connectors.yaml", SourceConnectorsRegistry
            ),
            monitoring=load_typed_yaml(self._config_dir / "monitoring.yaml", MonitoringRegistry),
            run_policies=load_typed_yaml(
                self._config_dir / "run_policies.yaml", RunPoliciesRegistry
            ),
        )
        self._validate_bundle(bundle)
        return bundle

    def _validate_bundle(self, bundle: RegistryBundle) -> None:
        panel_map = self._index_by_id("panel", bundle.panels.panels)
        factor_map = self._index_by_id("factor", bundle.factors.factors)
        memo_map = self._index_by_id("memo section", bundle.memo_sections.memo_sections)
        agent_map = self._index_by_id("agent", bundle.agents.agents)
        tool_map = self._index_by_id("tool", bundle.tool_registry.tools)
        tool_bundle_map = self._index_by_id("tool bundle", bundle.tool_bundles.bundles)

        allowed_agent_panels = set(panel_map) | set(INTERNAL_AGENT_PANEL_IDS)
        for panel in bundle.panels.panels:
            if panel.subgraph not in SUPPORTED_PANEL_SUBGRAPHS:
                raise ValueError(f"Unsupported panel subgraph for {panel.id}: {panel.subgraph}")
            self._validate_output_schema(panel.id, panel.output_schema)
            self._validate_prompt_path(panel.prompt_path)

            missing_sections = [
                section_id for section_id in panel.memo_section_ids if section_id not in memo_map
            ]
            if missing_sections:
                joined = ", ".join(sorted(missing_sections))
                raise ValueError(f"Panel {panel.id} references unknown memo sections: {joined}")

            missing_factors = [
                factor_id for factor_id in panel.factor_ids if factor_id not in factor_map
            ]
            if missing_factors:
                joined = ", ".join(sorted(missing_factors))
                raise ValueError(f"Panel {panel.id} references unknown factors: {joined}")

            mismatched_factors = [
                factor_id
                for factor_id in panel.factor_ids
                if factor_id in factor_map and factor_map[factor_id].panel_id != panel.id
            ]
            if mismatched_factors:
                joined = ", ".join(sorted(mismatched_factors))
                raise ValueError(
                    f"Panel {panel.id} includes factors owned by another panel: {joined}"
                )

        for factor in bundle.factors.factors:
            if factor.panel_id not in panel_map:
                raise ValueError(f"Factor {factor.id} references unknown panel: {factor.panel_id}")

        model_profile_ids = set(bundle.model_profiles.model_profiles)
        for agent in bundle.agents.agents:
            if agent.panel_id not in allowed_agent_panels:
                raise ValueError(f"Agent {agent.id} references unknown panel: {agent.panel_id}")
            if agent.parent_id is not None and agent.parent_id not in agent_map:
                raise ValueError(
                    f"Agent {agent.id} references unknown parent agent: {agent.parent_id}"
                )
            if agent.allowed_tool_bundle not in tool_bundle_map:
                raise ValueError(
                    f"Agent {agent.id} references unknown tool bundle: {agent.allowed_tool_bundle}"
                )
            if agent.model_profile not in model_profile_ids:
                raise ValueError(
                    f"Agent {agent.id} references unknown model profile: {agent.model_profile}"
                )
            self._validate_output_schema(agent.id, agent.output_schema)
            self._validate_prompt_path(agent.prompt_path)

        for bundle_config in bundle.tool_bundles.bundles:
            missing_tools = [
                tool_id for tool_id in bundle_config.tool_ids if tool_id not in tool_map
            ]
            if missing_tools:
                joined = ", ".join(sorted(missing_tools))
                raise ValueError(
                    f"Tool bundle {bundle_config.id} references unknown tools: {joined}"
                )

        for connector in bundle.source_connectors.connectors:
            if connector.kind == "file_bundle" and not connector.manifest_file:
                raise ValueError(
                    f"Connector {connector.id} must declare a manifest_file for kind=file_bundle"
                )

        for policy_name, policy in bundle.run_policies.run_policies.items():
            missing_panels = [
                panel_id for panel_id in policy.default_panel_ids if panel_id not in panel_map
            ]
            if missing_panels:
                joined = ", ".join(sorted(missing_panels))
                raise ValueError(f"Run policy {policy_name} references unknown panels: {joined}")

    def _index_by_id(self, label: str, entries: list[object]) -> dict[str, object]:
        indexed: dict[str, object] = {}
        for entry in entries:
            entry_id = entry.id
            if entry_id in indexed:
                raise ValueError(f"Duplicate {label} id detected: {entry_id}")
            indexed[entry_id] = entry
        return indexed

    def _validate_output_schema(self, owner_id: str, schema_name: str) -> None:
        if schema_name not in SUPPORTED_OUTPUT_SCHEMAS:
            raise ValueError(f"{owner_id} references unsupported output schema: {schema_name}")

    def _validate_prompt_path(self, prompt_path: str) -> None:
        if self._prompts_dir is None:
            return
        raw_path = Path(prompt_path)
        if raw_path.is_absolute():
            raise ValueError(f"Prompt path must be relative: {prompt_path}")
        if not raw_path.parts or raw_path.parts[0] != "prompts":
            raise ValueError(f"Prompt path must stay under prompts/: {prompt_path}")

        resolved_path = (self._prompts_dir / Path(*raw_path.parts[1:])).resolve()
        prompts_root = self._prompts_dir.resolve()
        try:
            resolved_path.relative_to(prompts_root)
        except ValueError as exc:
            raise ValueError(f"Prompt path escapes prompts directory: {prompt_path}") from exc
        if not resolved_path.is_file():
            raise ValueError(f"Prompt file does not exist: {prompt_path}")
