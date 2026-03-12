from __future__ import annotations

from fastapi.testclient import TestClient

from ai_investing.api.main import create_app
from ai_investing.domain.enums import RunContinueAction
from ai_investing.persistence.repositories import Repository


def _set_panel_policy(context, company_id: str, panel_policy: str) -> None:
    with context.database.session() as session:
        repository = Repository(session)
        coverage = repository.get_coverage(company_id)
        assert coverage is not None
        coverage.panel_policy = panel_policy
        repository.upsert_coverage(coverage)


def test_create_app_defers_context_loading_until_startup(context, monkeypatch) -> None:
    loaded = 0

    def load_context():
        nonlocal loaded
        loaded += 1
        return context

    monkeypatch.setattr("ai_investing.api.main.AppContext.load", load_context)

    app = create_app()

    assert loaded == 0
    with TestClient(app):
        assert loaded == 1


def test_api_lifespan_initializes_database(context) -> None:
    initialize_calls = 0
    original_initialize = type(context.database).initialize

    def tracked_initialize(database) -> None:
        nonlocal initialize_calls
        if database is context.database:
            initialize_calls += 1
        original_initialize(database)

    type(context.database).initialize = tracked_initialize  # type: ignore[assignment]

    with TestClient(create_app(context)) as client:
        response = client.get("/coverage")

    type(context.database).initialize = original_initialize  # type: ignore[assignment]

    assert response.status_code == 200
    assert response.json() == {"data": []}
    assert initialize_calls == 1


def test_api_preserves_phase_one_operator_routes(context) -> None:
    app = create_app(context)
    route_paths = {route.path for route in app.routes}

    assert "/coverage" in route_paths
    assert "/coverage/{company_id}/disable" in route_paths
    assert "/coverage/{company_id}" in route_paths
    assert "/coverage/{company_id}/next-run-at" in route_paths
    assert "/coverage/run-due" in route_paths
    assert "/companies/{company_id}/ingest-public" in route_paths
    assert "/companies/{company_id}/ingest-private" in route_paths
    assert "/companies/{company_id}/analyze" in route_paths
    assert "/companies/{company_id}/refresh" in route_paths
    assert "/runs/{run_id}" in route_paths
    assert "/runs/{run_id}/continue" in route_paths
    assert "/companies/{company_id}/panels/{panel_id}/run" in route_paths
    assert "/companies/{company_id}/memo" in route_paths
    assert "/companies/{company_id}/delta" in route_paths
    assert "/agents" in route_paths
    assert "/agents/{agent_id}/enable" in route_paths
    assert "/agents/{agent_id}/disable" in route_paths
    assert "/agents/{agent_id}/reparent" in route_paths


def test_api_returns_stable_not_found_error_shape(context) -> None:
    with TestClient(create_app(context)) as client:
        response = client.get("/companies/UNKNOWN/memo")

    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "not_found", "message": "UNKNOWN"},
    }


def test_api_coverage_lifecycle_and_agent_reparent(context) -> None:
    with TestClient(create_app(context)) as client:
        created = client.post(
            "/coverage",
            json={
                "company_id": "ACME",
                "company_name": "Acme Cloud",
                "company_type": "public",
                "coverage_status": "watchlist",
            },
        )
        assert created.status_code == 201

        updated = client.post(
            "/coverage/ACME/next-run-at",
            json={"next_run_at": "2026-03-10T09:30:00+00:00"},
        )
        assert updated.status_code == 200
        assert updated.json()["data"]["next_run_at"] == "2026-03-10T09:30:00Z"

        disabled = client.post("/coverage/ACME/disable")
        assert disabled.status_code == 200
        assert disabled.json()["data"]["enabled"] is False

        reparented = client.post(
            "/agents/demand_skeptic/reparent",
            json={"parent_id": "gatekeeper_advocate"},
        )
        assert reparented.status_code == 200
        assert reparented.json()["data"]["parent_id"] == "gatekeeper_advocate"

        removed = client.delete("/coverage/ACME")
        assert removed.status_code == 200
        assert removed.json() == {"data": {"company_id": "ACME", "removed": True}}


def test_api_rejects_company_id_mismatch_on_ingest(context, repo_root) -> None:
    with TestClient(create_app(context)) as client:
        response = client.post(
            "/companies/BETA/ingest-public",
            json={"input_dir": str(repo_root / "examples" / "acme_public")},
        )

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "code": "invalid_request",
            "message": "Path company_id BETA does not match manifest company_id ACME.",
        }
    }


def test_api_run_panel_and_continue_flow(seeded_acme) -> None:
    with TestClient(create_app(seeded_acme)) as client:
        invalid = client.post("/companies/ACME/panels/demand_revenue_quality/run")

        assert invalid.status_code == 400
        assert "gatekeepers" in invalid.json()["error"]["message"]

        paused = client.post("/companies/ACME/analyze")

        assert paused.status_code == 200
        paused_payload = paused.json()["data"]
        run_id = paused_payload["run"]["run_id"]
        assert paused_payload["run"]["status"] == "awaiting_continue"
        assert paused_payload["run"]["awaiting_continue"] is True
        assert paused_payload["run"]["checkpoint_panel_id"] == "gatekeepers"
        assert paused_payload["run"]["checkpoint"]["allowed_actions"] == ["stop", "continue"]

        shown = client.get(f"/runs/{run_id}")

        assert shown.status_code == 200
        shown_payload = shown.json()["data"]
        assert shown_payload["run"]["run_id"] == run_id
        assert shown_payload["run"]["status"] == "awaiting_continue"
        assert "gatekeepers" in shown_payload["panels"]
        assert shown_payload["delta"] is None

        resumed = client.post(f"/runs/{run_id}/continue", json={"action": "continue"})

        assert resumed.status_code == 200
        resumed_payload = resumed.json()["data"]
        assert resumed_payload["run"]["run_id"] == run_id
        assert resumed_payload["run"]["status"] == "complete"
        assert resumed_payload["memo"]["is_initial_coverage"] is True
        assert resumed_payload["delta"]["prior_run_id"] is None
        resumed_sections = {
            section["section_id"]: section for section in resumed_payload["memo"]["sections"]
        }
        assert resumed_sections["economic_spread"]["status"] == "not_advanced"


def test_api_run_panel_rejects_scaffold_only_panel(seeded_acme) -> None:
    with TestClient(create_app(seeded_acme)) as client:
        response = client.post("/companies/ACME/panels/supply_product_operations/run")

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "code": "invalid_request",
            "message": (
                "Panel supply_product_operations is not implemented for policy weekly_default."
            ),
        }
    }

    with seeded_acme.database.session() as session:
        runs = Repository(session).list_runs("ACME")

    assert runs == []


def test_api_analyze_rejects_full_surface_policy_without_partial_run(seeded_acme) -> None:
    _set_panel_policy(seeded_acme, "ACME", "full_surface")

    with TestClient(create_app(seeded_acme)) as client:
        response = client.post("/companies/ACME/analyze")

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "code": "invalid_request",
            "message": "Panel supply_product_operations is not implemented for policy full_surface.",
        }
    }

    with seeded_acme.database.session() as session:
        runs = Repository(session).list_runs("ACME")

    assert runs == []


def test_api_run_due_returns_paused_run_payload(seeded_acme) -> None:
    with TestClient(create_app(seeded_acme)) as client:
        first = client.post("/coverage/run-due")

        assert first.status_code == 200
        first_payload = first.json()["data"]
        first_run_id = first_payload[0]["run"]["run_id"]
        assert first_payload[0]["run"]["status"] == "awaiting_continue"
        assert first_payload[0]["run"]["awaiting_continue"] is True

        second = client.post("/coverage/run-due")

        assert second.status_code == 200
        second_payload = second.json()["data"]
        assert second_payload[0]["run"]["run_id"] == first_run_id
        assert second_payload[0]["run"]["checkpoint"]["allowed_actions"] == [
            "stop",
            "continue",
        ]


def test_api_continue_run_accepts_provisional_action(context, monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_continue_run(_service, run_id: str, action: RunContinueAction) -> dict[str, object]:
        captured["run_id"] = run_id
        captured["action"] = action
        return {
            "run": {
                "run_id": run_id,
                "company_id": "ACME",
                "run_kind": "analyze",
                "status": "provisional",
                "triggered_by": "system",
                "panel_id": None,
                "started_at": "2026-03-11T00:00:00Z",
                "completed_at": "2026-03-11T00:05:00Z",
                "gate_decision": "fail",
                "awaiting_continue": False,
                "gated_out": False,
                "provisional": True,
                "stopped_after_panel": None,
                "checkpoint_panel_id": "gatekeepers",
                "checkpoint": {
                    "checkpoint_panel_id": "gatekeepers",
                    "allowed_actions": ["stop", "continue_provisional"],
                    "provisional_required": True,
                    "note": "Gatekeepers failed. Continue only as provisional downstream analysis.",
                    "requested_at": "2026-03-11T00:00:00Z",
                    "resolved_at": "2026-03-11T00:05:00Z",
                    "resolution_action": "continue_provisional",
                },
                "metadata": {
                    "panel_ids": ["gatekeepers", "demand_revenue_quality"],
                },
            },
            "panels": {},
            "memo": None,
            "delta": None,
        }

    monkeypatch.setattr("ai_investing.api.main.AnalysisService.continue_run", fake_continue_run)

    with TestClient(create_app(context)) as client:
        response = client.post(
            "/runs/run_failed/continue",
            json={"action": "continue_provisional"},
        )

    assert response.status_code == 200
    assert captured == {
        "run_id": "run_failed",
        "action": RunContinueAction.CONTINUE_PROVISIONAL,
    }
    assert response.json()["data"]["run"]["provisional"] is True
