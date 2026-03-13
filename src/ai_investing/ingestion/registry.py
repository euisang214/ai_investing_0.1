from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from ai_investing.config.models import SourceConnectorConfig
from ai_investing.ingestion.base import ResolvedSourceConnector, SourceConnector
from ai_investing.ingestion.file_connectors import FileBundleConnector

ConnectorBuilder = Callable[[SourceConnectorConfig], SourceConnector]


def _build_file_bundle_connector(config: SourceConnectorConfig) -> SourceConnector:
    return FileBundleConnector(
        manifest_file=config.require_setting("manifest_file"),
        raw_landing_zone=Path(config.require_setting("raw_landing_zone")),
    )


@dataclass(frozen=True)
class SourceConnectorRegistry:
    connector_configs: dict[str, SourceConnectorConfig]
    builders: dict[str, ConnectorBuilder] = field(
        default_factory=lambda: {"file_bundle": _build_file_bundle_connector}
    )

    @classmethod
    def from_configs(cls, connectors: list[SourceConnectorConfig]) -> SourceConnectorRegistry:
        return cls(connector_configs={connector.id: connector for connector in connectors})

    def resolve(self, connector_id: str) -> ResolvedSourceConnector:
        connector_config = self.connector_configs.get(connector_id)
        if connector_config is None:
            raise ValueError(f"Unknown connector id: {connector_id}")

        builder = self.builders.get(connector_config.kind)
        if builder is None:
            raise ValueError(
                f"Connector {connector_id} has no runtime implementation for kind="
                f"{connector_config.kind}"
            )
        return ResolvedSourceConnector(
            config=connector_config,
            implementation=builder(connector_config),
        )
