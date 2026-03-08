from __future__ import annotations

from pathlib import Path
from typing import TypeVar

import yaml

from ai_investing.config.models import (
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
    def __init__(self, config_dir: Path):
        self._config_dir = config_dir

    def load_all(self) -> RegistryBundle:
        return RegistryBundle(
            panels=load_typed_yaml(self._config_dir / "panels.yaml", PanelsRegistry),
            factors=load_typed_yaml(self._config_dir / "factors.yaml", FactorsRegistry),
            memo_sections=load_typed_yaml(
                self._config_dir / "memo_sections.yaml", MemoSectionsRegistry
            ),
            agents=load_typed_yaml(self._config_dir / "agents.yaml", AgentsRegistry),
            model_profiles=load_typed_yaml(
                self._config_dir / "model_profiles.yaml", ModelProfilesRegistry
            ),
            tool_registry=load_typed_yaml(
                self._config_dir / "tool_registry.yaml", ToolRegistry
            ),
            tool_bundles=load_typed_yaml(
                self._config_dir / "tool_bundles.yaml", ToolBundlesRegistry
            ),
            source_connectors=load_typed_yaml(
                self._config_dir / "source_connectors.yaml", SourceConnectorsRegistry
            ),
            monitoring=load_typed_yaml(
                self._config_dir / "monitoring.yaml", MonitoringRegistry
            ),
            run_policies=load_typed_yaml(
                self._config_dir / "run_policies.yaml", RunPoliciesRegistry
            ),
        )

