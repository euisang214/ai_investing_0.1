from __future__ import annotations

from ai_investing.application.services import CoverageService, IngestionService
from ai_investing.domain.enums import Cadence, CompanyType, CoverageStatus
from ai_investing.domain.models import CoverageEntry
from ai_investing.monitoring import AnalogGraph, ClaimContradictionService
from ai_investing.persistence.repositories import Repository


def _seed_beta(context, repo_root) -> None:
    IngestionService(context).ingest_private_data(repo_root / "examples" / "beta_private")
    CoverageService(context).add_coverage(
        CoverageEntry(
            company_id="BETA",
            company_name="Beta Logistics Software",
            company_type=CompanyType.PRIVATE,
            coverage_status=CoverageStatus.WATCHLIST,
            cadence=Cadence.WEEKLY,
        )
    )


def test_analog_graph_returns_deterministic_ranked_references(seeded_acme, repo_root) -> None:
    _seed_beta(seeded_acme, repo_root)

    with seeded_acme.database.session() as session:
        repository = Repository(session)
        graph = AnalogGraph.from_mapping(
            seeded_acme.registries.monitoring.monitoring.analog.model_dump(mode="python")
        )
        first = graph.rank_company(
            repository,
            "ACME",
            factor_ids=["customer_concentration", "balance_sheet_survivability"],
        )
        second = graph.rank_company(
            repository,
            "ACME",
            factor_ids=["customer_concentration", "balance_sheet_survivability"],
        )

    assert first
    assert [reference.model_dump(mode="json") for reference in first] == [
        reference.model_dump(mode="json") for reference in second
    ]
    assert first[0].company_id == "BETA"
    assert first[0].category == "base_rate"
    assert first[0].score is not None and first[0].score >= 1.4


def test_analog_lookup_builtin_uses_shared_ranker(seeded_acme, repo_root) -> None:
    _seed_beta(seeded_acme, repo_root)

    agent = next(
        agent for agent in seeded_acme.registries.agents.agents if agent.id == "gatekeeper_panel_lead"
    )
    with seeded_acme.database.session() as session:
        repository = Repository(session)
        direct = AnalogGraph.from_mapping(
            seeded_acme.registries.monitoring.monitoring.analog.model_dump(mode="python")
        ).rank_company(
            repository,
            "ACME",
            factor_ids=["customer_concentration", "balance_sheet_survivability"],
        )
        tool_result = seeded_acme.tool_registry.execute(
            repository=repository,
            agent=agent,
            company_id="ACME",
            run_id="run_analog",
            tool_id="analog_lookup",
            payload={"factor_ids": ["customer_concentration", "balance_sheet_survivability"]},
        )

    assert tool_result["references"] == [reference.model_dump(mode="json") for reference in direct]


def test_contradiction_finder_builtin_uses_shared_service(seeded_acme, repo_root) -> None:
    service = seeded_acme.registries.monitoring.monitoring.contradiction.model_dump(mode="python")
    IngestionService(seeded_acme).ingest_public_data(repo_root / "examples" / "acme_public_rerun")
    agent = next(
        agent for agent in seeded_acme.registries.agents.agents if agent.id == "gatekeeper_panel_lead"
    )

    with seeded_acme.database.session() as session:
        repository = Repository(session)
        claims = repository.list_claim_cards("ACME", active_only=True)
        evidence = repository.list_evidence("ACME")
        direct = ClaimContradictionService.from_mapping(service).find_references(
            claims=claims,
            evidence_records=evidence,
            factor_ids=["customer_concentration"],
        )
        tool_result = seeded_acme.tool_registry.execute(
            repository=repository,
            agent=agent,
            company_id="ACME",
            run_id="run_contradiction",
            tool_id="contradiction_finder",
            payload={"factor_ids": ["customer_concentration"]},
        )

    assert tool_result["references"] == [reference.model_dump(mode="json") for reference in direct]
