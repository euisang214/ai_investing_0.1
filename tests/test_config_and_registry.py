from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from ai_investing.application.context import AppContext
from ai_investing.application.services import AgentConfigService
from ai_investing.config.loader import RegistryLoader
from ai_investing.domain.models import ClaimCard
from ai_investing.settings import Settings


def _settings_for(repo_root: Path, config_dir: Path, *, provider: str = "fake") -> Settings:
    return Settings(
        database_url="sqlite+pysqlite:///:memory:",
        config_dir=config_dir,
        prompts_dir=repo_root / "prompts",
        provider=provider,
    )


def _copy_config(repo_root: Path, tmp_path: Path) -> Path:
    config_dir = tmp_path / "config"
    shutil.copytree(repo_root / "config", config_dir)
    return config_dir


def test_config_loader_validates_registries(context) -> None:
    panels = {panel.id for panel in context.registries.panels.panels}
    assert "gatekeepers" in panels
    assert "demand_revenue_quality" in panels
    assert "portfolio_fit_positioning" in panels
    assert "balanced" in context.registries.model_profiles.model_profiles
    assert "gatekeeper_research" in {
        bundle.id for bundle in context.registries.tool_bundles.bundles
    }


def test_registry_loader_rejects_invalid_cross_references(repo_root, tmp_path) -> None:
    config_dir = _copy_config(repo_root, tmp_path)
    panels_path = config_dir / "panels.yaml"
    panels = yaml.safe_load(panels_path.read_text(encoding="utf-8"))
    panels["panels"][0]["memo_section_ids"].append("missing_section")
    panels_path.write_text(yaml.safe_dump(panels, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="unknown memo sections"):
        RegistryLoader(config_dir, prompts_dir=repo_root / "prompts").load_all()


def test_registry_loader_rejects_missing_builtin_tool_handler(repo_root, tmp_path) -> None:
    config_dir = _copy_config(repo_root, tmp_path)
    tool_registry_path = config_dir / "tool_registry.yaml"
    tool_registry = yaml.safe_load(tool_registry_path.read_text(encoding="utf-8"))
    for tool in tool_registry["tools"]:
        if tool["id"] == "evidence_search":
            tool["handler"] = "missing_handler"
            break
    tool_registry_path.write_text(
        yaml.safe_dump(tool_registry, sort_keys=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unknown handler"):
        AppContext.load(_settings_for(repo_root, config_dir))


def test_agent_config_updates_persist_and_reload(context) -> None:
    service = AgentConfigService(context)
    disabled = service.disable_agent("demand_skeptic")
    assert disabled.enabled is False

    reparsed = service.reparent_agent("demand_skeptic", "gatekeeper_advocate")
    assert reparsed.parent_id == "gatekeeper_advocate"

    enabled = service.enable_agent("demand_skeptic")
    assert enabled.enabled is True


def test_prompt_loader_rejects_escape_paths(context) -> None:
    with pytest.raises(ValueError, match="escapes prompts directory"):
        context.prompt_loader.resolve("prompts/../../secret.txt")


def test_explicit_provider_selection_requires_runtime_dependencies(
    repo_root, tmp_path, monkeypatch
) -> None:
    config_dir = _copy_config(repo_root, tmp_path)
    monkeypatch.setenv("OPENAI_MODEL_BALANCED", "gpt-4o-mini")
    app_context = AppContext.load(_settings_for(repo_root, config_dir, provider="openai"))

    with pytest.raises(RuntimeError, match="Install ai-investing\\[openai\\]"):
        app_context.get_provider("balanced")


def test_claim_card_schema_validation() -> None:
    with pytest.raises(ValueError):
        ClaimCard(
            company_id="ACME",
            company_type="public",
            run_id="run_1",
            panel_id="gatekeepers",
            factor_id="need_to_exist",
            agent_id="gatekeeper_advocate",
            claim="bad",
            bull_case="bad",
            bear_case="bad",
            confidence=1.4,
            evidence_quality=0.4,
            staleness_assessment="fresh",
            time_horizon="12 months",
            durability_horizon="multi-year",
            what_changed="none",
            namespace="company/ACME/claims/need_to_exist",
        )


def test_tool_registry_executes_builtin_handler_aliases(seeded_acme) -> None:
    agent = next(
        agent for agent in seeded_acme.registries.agents.agents if agent.id == "gatekeeper_advocate"
    )
    with seeded_acme.database.session() as session:
        from ai_investing.persistence.repositories import Repository

        repository = Repository(session)
        result = seeded_acme.tool_registry.execute(
            repository=repository,
            agent=agent,
            company_id="ACME",
            run_id="run_1",
            tool_id="filing_fetch",
            payload={"panel_id": "gatekeepers"},
        )

    assert "records" in result
