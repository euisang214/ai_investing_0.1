from __future__ import annotations

from fastapi.testclient import TestClient

from ai_investing.api.main import create_app


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
