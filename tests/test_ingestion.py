from __future__ import annotations

import json
import shutil
from pathlib import Path

import yaml

from ai_investing.application.context import AppContext
from ai_investing.application.services import IngestionService
from ai_investing.persistence.repositories import Repository
from ai_investing.settings import Settings


def _copy_config(repo_root: Path, tmp_path: Path) -> tuple[Path, dict]:
    config_dir = tmp_path / "config"
    shutil.copytree(repo_root / "config", config_dir)

    source_connectors_path = config_dir / "source_connectors.yaml"
    source_connectors = yaml.safe_load(source_connectors_path.read_text(encoding="utf-8"))
    for connector in source_connectors["connectors"]:
        connector["raw_landing_zone"] = str(tmp_path / connector["id"])
    source_connectors_path.write_text(
        yaml.safe_dump(source_connectors, sort_keys=False),
        encoding="utf-8",
    )
    return config_dir, source_connectors


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


def _evidence_for(context: AppContext, company_id: str) -> list:
    with context.database.session() as session:
        repository = Repository(session)
        return repository.list_evidence(company_id)


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
    assert len(evidence_ids) == 5


def test_ingestion_uses_configured_manifest_file(repo_root, tmp_path) -> None:
    config_dir, source_connectors = _copy_config(repo_root, tmp_path)
    for connector in source_connectors["connectors"]:
        if connector["id"] == "public_file_connector":
            connector["manifest_file"] = "bundle.json"
            connector["raw_landing_zone"] = str(tmp_path / "raw")
    (config_dir / "source_connectors.yaml").write_text(
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

    context = _load_context(repo_root, config_dir)
    profile, evidence_ids = IngestionService(context).ingest_public_data(input_dir)

    assert profile.company_id == "ACME"
    assert len(evidence_ids) == 3


def test_required_public_connector_families_emit_structured_evidence(repo_root, tmp_path) -> None:
    config_dir, _ = _copy_config(repo_root, tmp_path)
    context = _load_context(repo_root, config_dir)
    service = IngestionService(context)

    fixture_expectations = [
        ("acme_regulatory_packet", "regulatory", 1),
        ("acme_market_packet", "market", 2),
        ("acme_consensus_packet", "consensus", 2),
        ("acme_ownership_packet", "ownership", 2),
    ]
    for connector_id, family, expected_count in fixture_expectations:
        input_dir = repo_root / "examples" / "connectors" / connector_id
        profile, evidence_ids = service.ingest_public_data(input_dir, connector_id=connector_id)

        assert profile.company_id == "ACME"
        assert len(evidence_ids) == expected_count

        records = _evidence_for(context, "ACME")
        family_records = [
            record for record in records if record.metadata.get("connector") == connector_id
        ]
        assert len(family_records) == expected_count
        actual_families = {record.metadata["evidence_family"] for record in family_records}
        if connector_id == "acme_consensus_packet":
            assert actual_families == {"consensus", "market"}
        else:
            assert actual_families == {family}
        assert all(record.factor_ids for record in family_records)
        assert all(record.panel_ids for record in family_records)
        assert all(record.evidence_quality > 0.6 for record in family_records)
        assert all(record.staleness_days >= 0 for record in family_records)
        assert all(record.metadata["attachment_only"] is False for record in family_records)
        assert all(record.metadata["extracted_text"] is True for record in family_records)


def test_events_and_transcript_news_packets_keep_attachment_policy_honest(
    repo_root,
    tmp_path,
) -> None:
    config_dir, _ = _copy_config(repo_root, tmp_path)
    context = _load_context(repo_root, config_dir)
    service = IngestionService(context)

    service.ingest_public_data(
        repo_root / "examples" / "connectors" / "acme_events_packet",
        connector_id="acme_events_packet",
    )
    service.ingest_public_data(
        repo_root / "examples" / "connectors" / "acme_transcript_news_packet",
        connector_id="acme_transcript_news_packet",
    )

    records = _evidence_for(context, "ACME")
    events_records = [
        record for record in records if record.metadata.get("connector") == "acme_events_packet"
    ]
    transcript_records = [
        record
        for record in records
        if record.metadata.get("connector") == "acme_transcript_news_packet"
    ]

    assert len(events_records) == 3
    assert {record.source_type for record in events_records} == {"event_page", "event_image"}
    assert all(record.metadata["attachment_only"] is True for record in events_records)
    assert all("Attachment-only" in record.body for record in events_records)
    assert len(transcript_records) == 2
    assert all(record.metadata["attachment_only"] is False for record in transcript_records)
    assert any(
        "workflow usage stayed steady" in record.body.lower()
        for record in transcript_records
    )
    assert any(
        "trade press still places acme" in record.body.lower()
        for record in transcript_records
    )


def test_pdf_and_spreadsheet_packets_become_first_class_evidence(repo_root, tmp_path) -> None:
    config_dir, _ = _copy_config(repo_root, tmp_path)
    context = _load_context(repo_root, config_dir)
    service = IngestionService(context)

    service.ingest_private_data(
        repo_root / "examples" / "connectors" / "beta_dataroom",
        connector_id="beta_dataroom",
    )
    service.ingest_private_data(
        repo_root / "examples" / "connectors" / "beta_kpi_packet",
        connector_id="beta_kpi_packet",
    )

    records = _evidence_for(context, "BETA")
    pdf_record = next(record for record in records if record.source_type == "board_deck")
    xlsx_record = next(record for record in records if record.source_type == "kpi_workbook")

    assert pdf_record.metadata["media_type"] == "pdf"
    assert pdf_record.metadata["attachment_only"] is False
    assert "board packet pdf" in pdf_record.body.lower()
    assert "runway 17 months" in pdf_record.body.lower()

    assert xlsx_record.metadata["media_type"] == "spreadsheet"
    assert xlsx_record.metadata["attachment_only"] is False
    assert "metric,week_9_2026" in xlsx_record.body.lower()
    assert "net_revenue_retention_pct" in xlsx_record.body.lower()


def test_duplicate_raw_artifact_names_are_renamed_deterministically(repo_root, tmp_path) -> None:
    config_dir, _ = _copy_config(repo_root, tmp_path)
    context = _load_context(repo_root, config_dir)

    input_dir = tmp_path / "duplicate_bundle"
    (input_dir / "finance").mkdir(parents=True)
    (input_dir / "ops").mkdir(parents=True)
    (input_dir / "finance" / "summary.md").write_text(
        "Finance summary keeps renewal uplift intact.",
        encoding="utf-8",
    )
    (input_dir / "ops" / "summary.md").write_text(
        "Ops summary highlights implementation churn risk.",
        encoding="utf-8",
    )
    (input_dir / "manifest.json").write_text(
        json.dumps(
            {
                "company_id": "ACME",
                "company_name": "Acme Cloud",
                "company_type": "public",
                "description": "Duplicate filename fixture.",
                "documents": [
                    {
                        "path": "finance/summary.md",
                        "source_type": "market_commentary",
                        "title": "Finance Summary",
                        "as_of_date": "2026-03-04T00:00:00Z",
                        "panel_ids": ["demand_revenue_quality"],
                        "factor_ids": ["pricing_power"],
                        "factor_signals": {
                            "pricing_power": {
                                "stance": "positive",
                                "summary": "Renewal pricing remains firm.",
                                "metrics": {"renewal_uplift_pct": 6.0},
                            }
                        },
                        "source_refs": [{"label": "Finance Summary"}],
                        "metadata": {"connector": "public_file_connector"},
                    },
                    {
                        "path": "ops/summary.md",
                        "source_type": "public_news",
                        "title": "Ops Summary",
                        "as_of_date": "2026-03-04T00:00:00Z",
                        "panel_ids": ["gatekeepers"],
                        "factor_ids": ["fad_fashion_risk"],
                        "factor_signals": {
                            "fad_fashion_risk": {
                                "stance": "negative",
                                "summary": "Implementation friction remains visible.",
                                "metrics": {"headline_share_pct": 38.0},
                            }
                        },
                        "source_refs": [{"label": "Ops Summary"}],
                        "metadata": {"connector": "public_file_connector"},
                    },
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    profile, evidence_ids = IngestionService(context).ingest_public_data(input_dir)

    assert profile.company_id == "ACME"
    assert len(evidence_ids) == 2
    raw_names = sorted(
        Path(record.source_path).name for record in _evidence_for(context, "ACME")
    )
    assert raw_names == ["finance__summary.md", "ops__summary.md"]


def test_raw_artifacts_stay_flattened_under_connector_specific_landing_zones(
    repo_root,
    tmp_path,
) -> None:
    config_dir, source_connectors = _copy_config(repo_root, tmp_path)
    context = _load_context(repo_root, config_dir)

    connector_id = "acme_market_packet"
    profile, _ = IngestionService(context).ingest_public_data(
        repo_root / "examples" / "connectors" / connector_id,
        connector_id=connector_id,
    )
    records = _evidence_for(context, profile.company_id)
    landing_root = Path(
        next(
            connector["raw_landing_zone"]
            for connector in source_connectors["connectors"]
            if connector["id"] == connector_id
        )
    )

    assert records
    assert all(record.source_path.startswith(str(landing_root)) for record in records)
    assert all(
        Path(record.source_path).parent.parent == landing_root / profile.company_id
        for record in records
    )
    assert all(Path(record.source_path).parent.name.endswith("Z") for record in records)
