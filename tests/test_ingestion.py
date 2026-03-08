from __future__ import annotations

from ai_investing.application.services import IngestionService
from ai_investing.persistence.repositories import Repository


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
