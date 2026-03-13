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

EXPECTED_SCAFFOLD_PANEL_IDS = {
    "expectations_catalyst_realization",
    "external_regulatory_geopolitical",
    "financial_quality_liquidity_economic_model",
    "macro_industry_transmission",
    "management_governance_capital_allocation",
    "market_structure_growth",
    "portfolio_fit_positioning",
    "security_or_deal_overlay",
    "supply_product_operations",
}


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


def _scaffold_panels(context) -> list:
    return [panel for panel in context.registries.panels.panels if not panel.implemented]


def test_config_loader_validates_registries(context) -> None:
    panels = {panel.id for panel in context.registries.panels.panels}
    assert "gatekeepers" in panels
    assert "demand_revenue_quality" in panels
    assert "portfolio_fit_positioning" in panels
    assert "balanced" in context.registries.model_profiles.model_profiles
    assert "gatekeeper_research" in {
        bundle.id for bundle in context.registries.tool_bundles.bundles
    }


def test_scaffold_panels_materialize_in_registry_without_active_agents(context) -> None:
    scaffold_panels = _scaffold_panels(context)
    scaffold_panel_ids = {panel.id for panel in scaffold_panels}

    assert scaffold_panel_ids == EXPECTED_SCAFFOLD_PANEL_IDS
    for panel in scaffold_panels:
        assert context.get_panel(panel.id).implemented is False
        assert context.active_agents_for_panel(panel.id) == []


def test_scaffold_panels_have_one_disabled_placeholder_lead(context) -> None:
    scaffold_panels = _scaffold_panels(context)
    placeholder_agents = {
        panel.id: [
            agent
            for agent in context.registries.agents.agents
            if agent.panel_id == panel.id and agent.role_type == "lead" and not agent.enabled
        ]
        for panel in scaffold_panels
    }

    for panel in scaffold_panels:
        assert len(placeholder_agents[panel.id]) == 1, panel.id
        placeholder = placeholder_agents[panel.id][0]
        assert placeholder.prompt_path == panel.prompt_path
        assert "placeholder" in placeholder.tags
        assert "scaffold_only" in placeholder.tags


def test_scaffold_panels_reference_existing_prompts_and_owned_factors(
    context, repo_root
) -> None:
    scaffold_panels = _scaffold_panels(context)
    factor_owner = {
        factor.id: factor.panel_id for factor in context.registries.factors.factors
    }

    for panel in scaffold_panels:
        prompt_path = repo_root / panel.prompt_path
        assert prompt_path.is_file(), panel.prompt_path
        assert panel.factor_ids, panel.id
        assert all(factor_owner.get(factor_id) == panel.id for factor_id in panel.factor_ids), (
            panel.id
        )


def test_registry_loader_rejects_invalid_cross_references(repo_root, tmp_path) -> None:
    config_dir = _copy_config(repo_root, tmp_path)
    panels_path = config_dir / "panels.yaml"
    panels = yaml.safe_load(panels_path.read_text(encoding="utf-8"))
    panels["panels"][0]["memo_section_ids"].append("missing_section")
    panels_path.write_text(yaml.safe_dump(panels, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="unknown memo sections"):
        RegistryLoader(config_dir, prompts_dir=repo_root / "prompts").load_all()


def test_connector_registry_keeps_legacy_shape_backward_compatible(context) -> None:
    connectors = {
        connector.id: connector for connector in context.registries.source_connectors.connectors
    }
    public_connector = connectors["public_file_connector"]

    assert public_connector.kind == "file_bundle"
    assert public_connector.manifest_file == "manifest.json"
    assert public_connector.settings.manifest_file == "manifest.json"
    assert public_connector.raw_landing_zone.endswith("public_file_connector")
    assert public_connector.settings.raw_landing_zone.endswith("public_file_connector")
    assert public_connector.live_refresh.posture == "static"
    assert public_connector.evidence_policy.attachment_handling == "copy_to_raw"


def test_connector_registry_accepts_explicit_settings_and_policy_fields(
    repo_root, tmp_path
) -> None:
    config_dir = _copy_config(repo_root, tmp_path)
    source_connectors_path = config_dir / "source_connectors.yaml"
    source_connectors = yaml.safe_load(source_connectors_path.read_text(encoding="utf-8"))
    for connector in source_connectors["connectors"]:
        if connector["id"] == "public_file_connector":
            connector.pop("manifest_file", None)
            connector.pop("raw_landing_zone", None)
            connector["settings"] = {
                "manifest_file": "manifest.json",
                "raw_landing_zone": str(tmp_path / "raw-public"),
                "batch_size": 25,
            }
            connector["live_refresh"] = {
                "posture": "scheduled",
                "cadence": "0 6 * * 1",
                "max_staleness_hours": 72,
            }
            connector["evidence_policy"] = {
                "extraction_mode": "metadata_only",
                "attachment_handling": "reference_only",
            }
            connector["capabilities"] = ["structured_evidence", "live_refresh"]
            break
    source_connectors_path.write_text(
        yaml.safe_dump(source_connectors, sort_keys=False),
        encoding="utf-8",
    )

    registries = RegistryLoader(config_dir, prompts_dir=repo_root / "prompts").load_all()
    connector = next(
        item
        for item in registries.source_connectors.connectors
        if item.id == "public_file_connector"
    )

    assert connector.manifest_file == "manifest.json"
    assert connector.raw_landing_zone == str(tmp_path / "raw-public")
    assert connector.settings.model_extra["batch_size"] == 25
    assert connector.live_refresh.posture == "scheduled"
    assert connector.evidence_policy.extraction_mode == "metadata_only"
    assert connector.capabilities == ["structured_evidence", "live_refresh"]


def test_registry_loader_rejects_unknown_connector_kind(repo_root, tmp_path) -> None:
    config_dir = _copy_config(repo_root, tmp_path)
    source_connectors_path = config_dir / "source_connectors.yaml"
    source_connectors = yaml.safe_load(source_connectors_path.read_text(encoding="utf-8"))
    source_connectors["connectors"][0]["kind"] = "mystery_api"
    source_connectors_path.write_text(
        yaml.safe_dump(source_connectors, sort_keys=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Unsupported connector kind"):
        RegistryLoader(config_dir, prompts_dir=repo_root / "prompts").load_all()


def test_registry_loader_rejects_missing_required_connector_settings(repo_root, tmp_path) -> None:
    config_dir = _copy_config(repo_root, tmp_path)
    source_connectors_path = config_dir / "source_connectors.yaml"
    source_connectors = yaml.safe_load(source_connectors_path.read_text(encoding="utf-8"))
    for connector in source_connectors["connectors"]:
        if connector["id"] == "public_file_connector":
            connector.pop("manifest_file", None)
            connector["settings"] = {"raw_landing_zone": connector["raw_landing_zone"]}
            break
    source_connectors_path.write_text(
        yaml.safe_dump(source_connectors, sort_keys=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing required settings"):
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
