"""Tests for deployment: health probes, credential safety, and Dockerfile structure."""

from __future__ import annotations

import shutil
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from fastapi.testclient import TestClient

from ai_investing.api.main import create_app
from ai_investing.application.context import AppContext, _validate_production_settings
from ai_investing.settings import Settings


def _make_context(
    tmp_path: Path,
    repo_root: Path,
    *,
    auth_enabled: bool = False,
    api_keys: str = "",
    domain: str = "",
) -> AppContext:
    """Create an in-memory AppContext with specific settings."""
    config_dir = tmp_path / "config"
    if not config_dir.exists():
        shutil.copytree(repo_root / "config", config_dir)
        source_connectors_path = config_dir / "source_connectors.yaml"
        source_data = yaml.safe_load(
            source_connectors_path.read_text(encoding="utf-8"),
        )
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
# Health endpoints
# ---------------------------------------------------------------------------


class TestHealthEndpoints:
    def test_health_returns_ok(self, tmp_path, repo_root) -> None:
        ctx = _make_context(tmp_path, repo_root)
        with TestClient(create_app(ctx)) as client:
            r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}

    def test_health_skips_auth(self, tmp_path, repo_root) -> None:
        ctx = _make_context(
            tmp_path,
            repo_root,
            auth_enabled=True,
            api_keys="sk-test:operator",
        )
        with TestClient(create_app(ctx)) as client:
            # No X-API-Key header — should still get 200 (not 401)
            r = client.get("/health")
        assert r.status_code == 200

    def test_ready_returns_ok_when_db_reachable(
        self, tmp_path, repo_root,
    ) -> None:
        ctx = _make_context(tmp_path, repo_root)
        with TestClient(create_app(ctx)) as client:
            r = client.get("/ready")
        assert r.status_code == 200
        assert r.json() == {
            "status": "ready",
            "checks": {"database": "ok"},
        }

    def test_ready_skips_auth(self, tmp_path, repo_root) -> None:
        ctx = _make_context(
            tmp_path,
            repo_root,
            auth_enabled=True,
            api_keys="sk-test:operator",
        )
        with TestClient(create_app(ctx)) as client:
            r = client.get("/ready")
        assert r.status_code == 200

    def test_ready_returns_503_when_db_unreachable(
        self, tmp_path, repo_root,
    ) -> None:
        ctx = _make_context(tmp_path, repo_root)
        with patch.object(
            type(ctx.database), "ping", return_value=False,
        ):
            with TestClient(create_app(ctx)) as client:
                r = client.get("/ready")
        assert r.status_code == 503
        assert r.json() == {
            "status": "not_ready",
            "checks": {"database": "unreachable"},
        }


# ---------------------------------------------------------------------------
# Credential safety (unit tests for _validate_production_settings)
# ---------------------------------------------------------------------------


class TestCredentialSafety:
    def test_dev_mode_allows_default_credentials(self) -> None:
        """auth_enabled=False + postgres:postgres → no error."""
        settings = Settings(
            auth_enabled=False,
            database_url="postgresql+psycopg://postgres:postgres@db:5432/ai",
        )
        # Should NOT raise
        _validate_production_settings(settings)

    def test_prod_mode_blocks_default_credentials(self) -> None:
        """auth_enabled=True + postgres:postgres@ → SystemExit."""
        settings = Settings(
            auth_enabled=True,
            database_url="postgresql+psycopg://postgres:postgres@db:5432/ai",
        )
        with pytest.raises(SystemExit, match="FATAL"):
            _validate_production_settings(settings)

    def test_prod_mode_allows_secure_credentials(self) -> None:
        """auth_enabled=True + secure credentials → no error."""
        settings = Settings(
            auth_enabled=True,
            database_url="postgresql+psycopg://secure_user:s3cr3t@db:5432/ai",
        )
        # Should NOT raise
        _validate_production_settings(settings)

    def test_prod_mode_allows_sqlite_memory(self) -> None:
        """auth_enabled=True + sqlite memory → no error (test convenience)."""
        settings = Settings(
            auth_enabled=True,
            database_url="sqlite+pysqlite:///:memory:",
        )
        _validate_production_settings(settings)


# ---------------------------------------------------------------------------
# Dockerfile structure (read from project root, not /app)
# ---------------------------------------------------------------------------

def _find_dockerfile() -> Path | None:
    """Locate Dockerfile — works both locally and inside Docker."""
    candidates = [
        Path(__file__).resolve().parent.parent / "Dockerfile",
        Path("/app/Dockerfile"),
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


_DOCKERFILE_PATH = _find_dockerfile()


class TestDockerfileStructure:
    @pytest.mark.skipif(
        _DOCKERFILE_PATH is None,
        reason="Dockerfile not in expected location",
    )
    def test_prod_dockerfile_target_exists(self) -> None:
        content = _DOCKERFILE_PATH.read_text()
        assert "FROM base AS prod" in content

    @pytest.mark.skipif(
        _DOCKERFILE_PATH is None,
        reason="Dockerfile not in expected location",
    )
    def test_dev_dockerfile_target_exists(self) -> None:
        content = _DOCKERFILE_PATH.read_text()
        assert "FROM base AS dev" in content

    @pytest.mark.skipif(
        _DOCKERFILE_PATH is None,
        reason="Dockerfile not in expected location",
    )
    def test_prod_stage_does_not_copy_tests(self) -> None:
        content = _DOCKERFILE_PATH.read_text()
        stages = content.split("FROM base AS")
        prod_stage = [s for s in stages if s.strip().startswith("prod")]
        assert len(prod_stage) == 1
        assert "tests" not in prod_stage[0]
        assert "examples" not in prod_stage[0]
        assert "docs" not in prod_stage[0]

    @pytest.mark.skipif(
        _DOCKERFILE_PATH is None,
        reason="Dockerfile not in expected location",
    )
    def test_dev_stage_copies_tests(self) -> None:
        content = _DOCKERFILE_PATH.read_text()
        stages = content.split("FROM base AS")
        dev_stage = [s for s in stages if s.strip().startswith("dev")]
        assert len(dev_stage) == 1
        assert "tests" in dev_stage[0]
