"""Tests for API security: authentication, authorization, and CORS."""

from __future__ import annotations

import shutil

import yaml
from fastapi.testclient import TestClient

from ai_investing.api.main import create_app
from ai_investing.api.security import parse_api_keys
from ai_investing.application.context import AppContext
from ai_investing.settings import Settings

_OPERATOR_KEY = "sk-op-test"
_READONLY_KEY = "sk-ro-test"
_KEYS_ENV = f"{_OPERATOR_KEY}:operator,{_READONLY_KEY}:readonly"


def _make_context(
    tmp_path,
    repo_root,
    *,
    auth_enabled: bool = True,
    api_keys: str = "",
    domain: str = "",
) -> AppContext:
    """Create an AppContext with specific security settings."""
    config_dir = tmp_path / "config"
    if not config_dir.exists():
        shutil.copytree(repo_root / "config", config_dir)
        source_connectors_path = config_dir / "source_connectors.yaml"
        source_data = yaml.safe_load(source_connectors_path.read_text(encoding="utf-8"))
        for connector in source_data["connectors"]:
            connector["raw_landing_zone"] = str(tmp_path / connector["id"])
        source_connectors_path.write_text(
            yaml.safe_dump(source_data, sort_keys=False),
            encoding="utf-8",
        )
    settings = Settings(
        database_url="sqlite+pysqlite:///:memory:",
        config_dir=config_dir,
        prompts_dir=repo_root / "prompts",
        provider="fake",
        auth_enabled=auth_enabled,
        api_keys=api_keys,
        domain=domain,
    )
    ctx = AppContext.load(settings)
    ctx.database.initialize()
    return ctx


# ---------------------------------------------------------------------------
# parse_api_keys
# ---------------------------------------------------------------------------

class TestParseApiKeys:
    def test_parse_valid_keys(self) -> None:
        result = parse_api_keys("key1:operator,key2:readonly")
        assert result == {"key1": "operator", "key2": "readonly"}

    def test_parse_empty_string(self) -> None:
        assert parse_api_keys("") == {}

    def test_parse_whitespace(self) -> None:
        assert parse_api_keys("  ") == {}

    def test_parse_single_key(self) -> None:
        result = parse_api_keys("sk-abc:operator")
        assert result == {"sk-abc": "operator"}

    def test_parse_with_spaces(self) -> None:
        result = parse_api_keys("  key1 : operator , key2 : readonly  ")
        assert result == {"key1": "operator", "key2": "readonly"}

    def test_parse_ignores_malformed_entries(self) -> None:
        result = parse_api_keys("good:operator,bad,also-good:readonly")
        assert result == {"good": "operator", "also-good": "readonly"}


# ---------------------------------------------------------------------------
# Auth bypass (auth_enabled=false or no keys)
# ---------------------------------------------------------------------------

class TestAuthBypass:
    def test_auth_disabled_allows_all_requests(self, tmp_path, repo_root) -> None:
        ctx = _make_context(tmp_path, repo_root, auth_enabled=False)
        with TestClient(create_app(ctx)) as client:
            response = client.get("/coverage")
        assert response.status_code == 200

    def test_default_role_is_operator_when_auth_disabled(self, tmp_path, repo_root) -> None:
        ctx = _make_context(tmp_path, repo_root, auth_enabled=False)
        with TestClient(create_app(ctx)) as client:
            # Operator-only endpoint should work without any key
            response = client.post(
                "/coverage",
                json={
                    "company_id": "TEST",
                    "company_name": "Test Co",
                    "company_type": "public",
                    "coverage_status": "watchlist",
                },
            )
        assert response.status_code == 201

    def test_no_keys_configured_skips_auth(self, tmp_path, repo_root) -> None:
        """When auth_enabled=true but no keys are configured, auth is effectively off."""
        ctx = _make_context(tmp_path, repo_root, auth_enabled=True, api_keys="")
        with TestClient(create_app(ctx)) as client:
            response = client.get("/coverage")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Auth middleware (401)
# ---------------------------------------------------------------------------

class TestAuthMiddleware:
    def test_missing_api_key_returns_401(self, tmp_path, repo_root) -> None:
        ctx = _make_context(tmp_path, repo_root, auth_enabled=True, api_keys=_KEYS_ENV)
        with TestClient(create_app(ctx)) as client:
            response = client.get("/coverage")
        assert response.status_code == 401

    def test_invalid_api_key_returns_401(self, tmp_path, repo_root) -> None:
        ctx = _make_context(tmp_path, repo_root, auth_enabled=True, api_keys=_KEYS_ENV)
        with TestClient(create_app(ctx)) as client:
            response = client.get("/coverage", headers={"X-API-Key": "bogus"})
        assert response.status_code == 401

    def test_valid_api_key_passes_through(self, tmp_path, repo_root) -> None:
        ctx = _make_context(tmp_path, repo_root, auth_enabled=True, api_keys=_KEYS_ENV)
        with TestClient(create_app(ctx)) as client:
            response = client.get("/coverage", headers={"X-API-Key": _OPERATOR_KEY})
        assert response.status_code == 200

    def test_error_response_format(self, tmp_path, repo_root) -> None:
        ctx = _make_context(tmp_path, repo_root, auth_enabled=True, api_keys=_KEYS_ENV)
        with TestClient(create_app(ctx)) as client:
            response = client.get("/coverage")
        body = response.json()
        assert body == {
            "error": {
                "code": "unauthorized",
                "message": "Missing or invalid API key",
            }
        }


# ---------------------------------------------------------------------------
# Role-based access (403)
# ---------------------------------------------------------------------------

class TestRoleBasedAccess:
    def test_operator_key_accesses_operator_endpoint(self, tmp_path, repo_root) -> None:
        ctx = _make_context(tmp_path, repo_root, auth_enabled=True, api_keys=_KEYS_ENV)
        with TestClient(create_app(ctx)) as client:
            response = client.post(
                "/coverage",
                json={
                    "company_id": "TEST",
                    "company_name": "Test Co",
                    "company_type": "public",
                    "coverage_status": "watchlist",
                },
                headers={"X-API-Key": _OPERATOR_KEY},
            )
        assert response.status_code == 201

    def test_readonly_key_blocked_from_operator_endpoint(self, tmp_path, repo_root) -> None:
        ctx = _make_context(tmp_path, repo_root, auth_enabled=True, api_keys=_KEYS_ENV)
        with TestClient(create_app(ctx)) as client:
            response = client.post(
                "/coverage",
                json={
                    "company_id": "TEST",
                    "company_name": "Test Co",
                    "company_type": "public",
                    "coverage_status": "watchlist",
                },
                headers={"X-API-Key": _READONLY_KEY},
            )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"

    def test_readonly_key_accesses_readonly_endpoint(self, tmp_path, repo_root) -> None:
        ctx = _make_context(tmp_path, repo_root, auth_enabled=True, api_keys=_KEYS_ENV)
        with TestClient(create_app(ctx)) as client:
            response = client.get(
                "/coverage",
                headers={"X-API-Key": _READONLY_KEY},
            )
        assert response.status_code == 200

    def test_operator_key_accesses_readonly_endpoint(self, tmp_path, repo_root) -> None:
        ctx = _make_context(tmp_path, repo_root, auth_enabled=True, api_keys=_KEYS_ENV)
        with TestClient(create_app(ctx)) as client:
            response = client.get(
                "/coverage",
                headers={"X-API-Key": _OPERATOR_KEY},
            )
        assert response.status_code == 200

    def test_all_operator_endpoints_return_403_for_readonly(
        self,
        tmp_path,
        repo_root,
    ) -> None:
        """Every operator-only endpoint should return 403 for a readonly key."""
        ctx = _make_context(tmp_path, repo_root, auth_enabled=True, api_keys=_KEYS_ENV)
        headers = {"X-API-Key": _READONLY_KEY}

        # Route patterns for operator-only endpoints
        operator_routes = [
            ("POST", "/coverage"),
            ("POST", "/coverage/NOOP/disable"),
            ("DELETE", "/coverage/NOOP"),
            ("POST", "/coverage/NOOP/next-run-at"),
            ("POST", "/coverage/NOOP/schedule"),
            ("POST", "/coverage/run-due"),
            ("POST", "/queue/enqueue-selected"),
            ("POST", "/queue/enqueue-watchlist"),
            ("POST", "/queue/enqueue-portfolio"),
            ("POST", "/queue/enqueue-due"),
            ("POST", "/queue/NOOP/retry"),
            ("POST", "/queue/NOOP/cancel"),
            ("POST", "/queue/NOOP/force-run"),
            ("POST", "/workers/run"),
            ("POST", "/runs/NOOP/continue"),
            ("POST", "/notifications/NOOP/dispatch"),
            ("POST", "/notifications/NOOP/fail"),
            ("POST", "/companies/NOOP/ingest-public"),
            ("POST", "/companies/NOOP/ingest-private"),
            ("POST", "/companies/NOOP/analyze"),
            ("POST", "/companies/NOOP/refresh"),
            ("POST", "/companies/NOOP/panels/NOOP/run"),
            ("POST", "/agents/NOOP/enable"),
            ("POST", "/agents/NOOP/disable"),
            ("POST", "/agents/NOOP/reparent"),
        ]

        with TestClient(create_app(ctx), raise_server_exceptions=False) as client:
            for method, path in operator_routes:
                if method == "POST":
                    response = client.post(path, headers=headers, json={})
                else:
                    response = client.delete(path, headers=headers)

                assert response.status_code == 403, (
                    f"{method} {path} returned {response.status_code}, expected 403"
                )


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

class TestCORS:
    def test_no_cors_headers_when_domain_empty(self, tmp_path, repo_root) -> None:
        ctx = _make_context(tmp_path, repo_root, auth_enabled=False, domain="")
        with TestClient(create_app(ctx)) as client:
            response = client.get(
                "/coverage",
                headers={"Origin": "http://evil.com"},
            )
        assert "access-control-allow-origin" not in response.headers

    def test_cors_headers_present_when_domain_set(self, tmp_path, repo_root) -> None:
        ctx = _make_context(
            tmp_path,
            repo_root,
            auth_enabled=False,
            domain="http://localhost:3000",
        )
        with TestClient(create_app(ctx)) as client:
            response = client.options(
                "/coverage",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "GET",
                },
            )
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"

    def test_cors_allows_configured_origin(self, tmp_path, repo_root) -> None:
        ctx = _make_context(
            tmp_path,
            repo_root,
            auth_enabled=False,
            domain="http://localhost:3000",
        )
        with TestClient(create_app(ctx)) as client:
            response = client.get(
                "/coverage",
                headers={"Origin": "http://localhost:3000"},
            )
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"

    def test_cors_rejects_unconfigured_origin(self, tmp_path, repo_root) -> None:
        ctx = _make_context(
            tmp_path,
            repo_root,
            auth_enabled=False,
            domain="http://localhost:3000",
        )
        with TestClient(create_app(ctx)) as client:
            response = client.get(
                "/coverage",
                headers={"Origin": "http://evil.com"},
            )
        assert "access-control-allow-origin" not in response.headers
