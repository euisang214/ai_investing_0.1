from __future__ import annotations

import shutil

import yaml

from ai_investing.application.context import AppContext
from ai_investing.application.services import IngestionService
from ai_investing.persistence.repositories import Repository
from ai_investing.settings import Settings


def test_ingestion_parser_persists_evidence(context, repo_root) -> None:
    service = IngestionService(context)
    profile, evidence_ids = service.ingest_public_data(repo_root / "examples" / "acme_public")
    assert profile.company_id == "ACME"
    assert len(evidence_ids) == 3

    with context.database.session() as session:
        repository = Repository(session)
        evidence = repository.list_evidence("ACME", panel_id="gatekeepers")
        assert len(evidence) == 3
        assert any("need_to_exist" in record.factor_signals for record in evidence)


def test_private_ingestion_supported(context, repo_root) -> None:
    profile, evidence_ids = IngestionService(context).ingest_private_data(
        repo_root / "examples" / "beta_private"
    )
    assert profile.company_type.value == "private"
    assert len(evidence_ids) == 2


def test_ingestion_uses_configured_manifest_file(repo_root, tmp_path) -> None:
    config_dir = tmp_path / "config"
    shutil.copytree(repo_root / "config", config_dir)

    source_connectors_path = config_dir / "source_connectors.yaml"
    source_connectors = yaml.safe_load(source_connectors_path.read_text(encoding="utf-8"))
    for connector in source_connectors["connectors"]:
        if connector["id"] == "public_file_connector":
            connector["manifest_file"] = "bundle.json"
            connector["raw_landing_zone"] = str(tmp_path / "raw")
    source_connectors_path.write_text(
        yaml.safe_dump(source_connectors, sort_keys=False),
        encoding="utf-8",
    )

    input_dir = tmp_path / "input"
    shutil.copytree(repo_root / "examples" / "acme_public", input_dir)
    (input_dir / "bundle.json").write_text(
        (input_dir / "manifest.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (input_dir / "manifest.json").unlink()

    context = AppContext.load(
        Settings(
            database_url="sqlite+pysqlite:///:memory:",
            config_dir=config_dir,
            prompts_dir=repo_root / "prompts",
            provider="fake",
        )
    )
    context.database.initialize()

    profile, evidence_ids = IngestionService(context).ingest_public_data(input_dir)

    assert profile.company_id == "ACME"
    assert len(evidence_ids) == 3
