from __future__ import annotations

from ai_investing.application.services import AnalysisService, RefreshRuntime
from ai_investing.domain.enums import RunKind, RunStatus
from ai_investing.domain.models import RunRecord
from ai_investing.graphs.company_refresh import build_company_refresh_graph
from ai_investing.persistence.repositories import Repository


def test_tool_bundle_enforcement(seeded_acme) -> None:
    agent = next(agent for agent in seeded_acme.registries.agents.agents if agent.id == "demand_advocate")
    with seeded_acme.database.session() as session:
        repository = Repository(session)
        result = seeded_acme.tool_registry.execute(
            repository=repository,
            agent=agent,
            company_id="ACME",
            run_id="run_1",
            tool_id="evidence_search",
            payload={"panel_id": "demand_revenue_quality"},
        )
        assert "records" in result

        try:
            seeded_acme.tool_registry.execute(
                repository=repository,
                agent=agent,
                company_id="ACME",
                run_id="run_1",
                tool_id="send_notification",
                payload={},
            )
        except PermissionError:
            pass
        else:  # pragma: no cover - explicit failure branch
            raise AssertionError("Expected PermissionError")


def test_graph_composition(seeded_acme) -> None:
    with seeded_acme.database.session() as session:
        repository = Repository(session)
        coverage = repository.get_coverage("ACME")
        profile = repository.get_company_profile("ACME")
        assert coverage is not None
        assert profile is not None
        run = RunRecord(
            company_id="ACME",
            run_kind=RunKind.ANALYZE,
            status=RunStatus.RUNNING,
        )
        repository.save_run(run)
        runtime = RefreshRuntime.create(
            context=seeded_acme,
            repository=repository,
            run=run,
            coverage=coverage,
            company_profile=profile,
        )
        graph = build_company_refresh_graph(
            runtime=runtime,
            panel_ids=["gatekeepers", "demand_revenue_quality"],
        )
        result = graph.invoke({"company_id": "ACME", "run_id": run.run_id})
        assert "memo" in result
        assert "delta" in result


def test_end_to_end_fake_provider_run(seeded_acme) -> None:
    result = AnalysisService(seeded_acme).analyze_company("ACME")
    assert "gatekeepers" in result["panels"]
    assert "demand_revenue_quality" in result["panels"]
    assert result["memo"]["company_id"] == "ACME"
    assert result["delta"]["company_id"] == "ACME"


def test_memo_section_update_semantics(seeded_acme) -> None:
    result = AnalysisService(seeded_acme).analyze_company("ACME")
    sections = {section["section_id"]: section for section in result["memo"]["sections"]}
    assert sections["investment_snapshot"]["status"] == "refreshed"
    assert sections["what_changed_since_last_run"]["status"] == "refreshed"


def test_memo_synthesis_from_panel_outputs(seeded_acme) -> None:
    AnalysisService(seeded_acme).analyze_company("ACME")
    memo = AnalysisService(seeded_acme).generate_memo("ACME")
    assert memo.recommendation_summary
    assert len(memo.sections) == 11


def test_weekly_rerun_generates_delta(seeded_acme, repo_root) -> None:
    service = AnalysisService(seeded_acme)
    first = service.analyze_company("ACME")
    assert first["delta"]["change_summary"].startswith("Initial coverage run")

    from ai_investing.application.services import IngestionService

    IngestionService(seeded_acme).ingest_public_data(repo_root / "examples" / "acme_public_rerun")
    second = service.refresh_company("ACME")
    assert second["delta"]["changed_sections"]
    assert "what_changed_since_last_run" in [
        section["section_id"] for section in second["memo"]["sections"]
    ]


def test_monitoring_thesis_drift_logic(seeded_acme, repo_root) -> None:
    service = AnalysisService(seeded_acme)
    service.analyze_company("ACME")

    from ai_investing.application.services import IngestionService

    IngestionService(seeded_acme).ingest_public_data(repo_root / "examples" / "acme_public_rerun")
    result = service.refresh_company("ACME")
    assert "concentration_increase" in result["delta"]["thesis_drift_flags"]


def test_run_due_coverage(seeded_acme) -> None:
    results = AnalysisService(seeded_acme).run_due_coverage()
    assert len(results) == 1
