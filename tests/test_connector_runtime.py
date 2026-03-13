from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from ai_investing.application.context import AppContext
from ai_investing.application.services import IngestionService
from ai_investing.ingestion.registry import SourceConnectorRegistry
from ai_investing.persistence.repositories import Repository
from ai_investing.settings import Settings


def _copy_config(repo_root: Path, tmp_path: Path) -> Path:
    config_dir = tmp_path / "config"
    shutil.copytree(repo_root / "config", config_dir)
    return config_dir


def _write_connector_landings(config_dir: Path, tmp_path: Path) -> dict:
    source_connectors_path = config_dir / "source_connectors.yaml"
    source_connectors = yaml.safe_load(source_connectors_path.read_text(encoding="utf-8"))
    for connector in source_connectors["connectors"]:
        connector["raw_landing_zone"] = str(tmp_path / connector["id"])
    source_connectors_path.write_text(
        yaml.safe_dump(source_connectors, sort_keys=False),
        encoding="utf-8",
    )
    return source_connectors


def _load_context(repo_root: Path, config_dir: Path) -> AppContext:
    context = AppContext.load(
        Settings(
            database_url="sqlite+pysqlite:///:memory:",
            config_dir=config_dir,
            prompts_dir=repo_root / "prompts",
            provider="fake",
        )
    )
    context.database.initialize()
    return context


def test_connector_runtime_uses_default_public_and_private_connectors(
    context: AppContext, repo_root: Path
) -> None:
    service = IngestionService(context)
    public_profile, _ = service.ingest_public_data(repo_root / "examples" / "acme_public")
    private_profile, _ = service.ingest_private_data(repo_root / "examples" / "beta_private")

    public_connector = next(
        connector
        for connector in context.registries.source_connectors.connectors
        if connector.id == "public_file_connector"
    )
    private_connector = next(
        connector
        for connector in context.registries.source_connectors.connectors
        if connector.id == "private_file_connector"
    )

    with context.database.session() as session:
        repository = Repository(session)
        public_records = repository.list_evidence(public_profile.company_id)
        private_records = repository.list_evidence(private_profile.company_id)

    assert public_profile.company_type.value == "public"
    assert private_profile.company_type.value == "private"
    assert public_records
    assert private_records
    assert all(
        record.source_path.startswith(public_connector.raw_landing_zone)
        for record in public_records
    )
    assert all(
        record.source_path.startswith(private_connector.raw_landing_zone)
        for record in private_records
    )


def test_connector_runtime_allows_explicit_connector_selection(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    config_dir = _copy_config(repo_root, tmp_path)
    source_connectors = _write_connector_landings(config_dir, tmp_path)
    public_connector = next(
        connector
        for connector in source_connectors["connectors"]
        if connector["id"] == "public_file_connector"
    )
    source_connectors["connectors"].append(
        {
            "id": "public_file_connector_alias",
            "company_type": "public",
            "kind": "file_bundle",
            "settings": {
                "manifest_file": public_connector["manifest_file"],
                "raw_landing_zone": str(tmp_path / "public_file_connector_alias"),
            },
            "capabilities": ["structured_evidence"],
        }
    )
    (config_dir / "source_connectors.yaml").write_text(
        yaml.safe_dump(source_connectors, sort_keys=False),
        encoding="utf-8",
    )

    context = _load_context(repo_root, config_dir)
    profile, evidence_ids = IngestionService(context).ingest_public_data(
        repo_root / "examples" / "acme_public",
        connector_id="public_file_connector_alias",
    )

    with context.database.session() as session:
        repository = Repository(session)
        records = repository.list_evidence(profile.company_id)

    assert profile.company_id == "ACME"
    assert len(evidence_ids) == 3
    assert records
    assert all(
        record.source_path.startswith(str(tmp_path / "public_file_connector_alias"))
        for record in records
    )


def test_connector_registry_resolves_configured_alias(
    repo_root: Path,
    tmp_path: Path,
) -> None:
    config_dir = _copy_config(repo_root, tmp_path)
    source_connectors = _write_connector_landings(config_dir, tmp_path)
    public_connector = next(
        connector
        for connector in source_connectors["connectors"]
        if connector["id"] == "public_file_connector"
    )
    source_connectors["connectors"].append(
        {
            "id": "public_file_connector_alias",
            "company_type": "public",
            "kind": "file_bundle",
            "settings": {
                "manifest_file": public_connector["manifest_file"],
                "raw_landing_zone": str(tmp_path / "public_file_connector_alias"),
            },
        }
    )
    (config_dir / "source_connectors.yaml").write_text(
        yaml.safe_dump(source_connectors, sort_keys=False),
        encoding="utf-8",
    )

    context = _load_context(repo_root, config_dir)
    registry = SourceConnectorRegistry.from_configs(context.registries.source_connectors.connectors)
    connector = registry.resolve("public_file_connector_alias")

    assert connector.id == "public_file_connector_alias"
    assert connector.config.require_setting("manifest_file") == "manifest.json"
    assert connector.config.require_setting("raw_landing_zone") == str(
        tmp_path / "public_file_connector_alias"
    )


def test_connector_runtime_rejects_unknown_connector_id(
    context: AppContext,
    repo_root: Path,
) -> None:
    with pytest.raises(ValueError, match="Unknown connector id: missing_connector"):
        IngestionService(context).ingest_public_data(
            repo_root / "examples" / "acme_public",
            connector_id="missing_connector",
        )
