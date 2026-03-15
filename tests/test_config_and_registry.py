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

EXPECTED_SCAFFOLD_PANEL_IDS: set[str] = set()
EXPECTED_WAVE1_PANEL_IDS = {
    "supply_product_operations",
    "management_governance_capital_allocation",
    "financial_quality_liquidity_economic_model",
}
EXPECTED_WAVE2_PANEL_IDS = {
    "market_structure_growth",
    "macro_industry_transmission",
    "external_regulatory_geopolitical",
}
EXPECTED_WAVE3_PANEL_IDS = {
    "expectations_catalyst_realization",
}
EXPECTED_WAVE4_PANEL_IDS = {
    "security_or_deal_overlay",
    "portfolio_fit_positioning",
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
    assert context.registries.cadence_policies.workspace_timezone == "America/New_York"
    assert context.registries.cadence_policies.default_policy_id == "weekly"
    cadence_policies = {
        policy.id: policy for policy in context.registries.cadence_policies.cadence_policies
    }
    assert set(cadence_policies) == {
        "weekly",
        "biweekly",
        "weekdays",
        "monthly",
        "custom_weekdays",
    }
    assert cadence_policies["custom_weekdays"].weekdays == ["tuesday", "thursday"]
    run_policies = context.registries.run_policies.run_policies
    assert set(run_policies) == {
        "weekly_default",
        "internal_company_quality",
        "external_company_quality",
        "expectations_rollout",
        "full_surface",
    }
    assert run_policies["weekly_default"].wave == 0
    assert run_policies["internal_company_quality"].default_panel_ids == [
        "gatekeepers",
        "demand_revenue_quality",
        "supply_product_operations",
        "management_governance_capital_allocation",
        "financial_quality_liquidity_economic_model",
    ]
    assert run_policies["external_company_quality"].default_panel_ids == [
        "gatekeepers",
        "demand_revenue_quality",
        "supply_product_operations",
        "management_governance_capital_allocation",
        "financial_quality_liquidity_economic_model",
        "market_structure_growth",
        "macro_industry_transmission",
        "external_regulatory_geopolitical",
    ]
    assert run_policies["full_surface"].wave == 4


def test_phase6_has_no_remaining_scaffold_panels(context) -> None:
    scaffold_panels = _scaffold_panels(context)
    scaffold_panel_ids = {panel.id for panel in scaffold_panels}

    assert scaffold_panel_ids == EXPECTED_SCAFFOLD_PANEL_IDS
    assert scaffold_panels == []


def test_supply_management_financial_panels_are_implemented_with_active_agents(context) -> None:
    expected_roles = {"specialist", "skeptic", "durability", "judge", "lead"}

    for panel_id in EXPECTED_WAVE1_PANEL_IDS:
        panel = context.get_panel(panel_id)
        active_agents = context.active_agents_for_panel(panel_id)

        assert panel.implemented is True
        assert panel.prompt_path.endswith("panel_lead.md")
        assert {agent.role_type for agent in active_agents} == expected_roles
        assert all(agent.enabled for agent in active_agents)


def test_market_macro_regulatory_panels_are_implemented_with_active_agents(context) -> None:
    expected_roles = {"specialist", "skeptic", "durability", "judge", "lead"}

    for panel_id in EXPECTED_WAVE2_PANEL_IDS:
        panel = context.get_panel(panel_id)
        active_agents = context.active_agents_for_panel(panel_id)

        assert panel.implemented is True
        assert panel.prompt_path.endswith("panel_lead.md")
        assert {agent.role_type for agent in active_agents} == expected_roles
        assert all(agent.enabled for agent in active_agents)


def test_expectations_panel_is_implemented_with_active_agents(context) -> None:
    expected_roles = {"specialist", "skeptic", "durability", "judge", "lead"}

    for panel_id in EXPECTED_WAVE3_PANEL_IDS:
        panel = context.get_panel(panel_id)
        active_agents = context.active_agents_for_panel(panel_id)

        assert panel.implemented is True
        assert panel.prompt_path.endswith("panel_lead.md")
        assert {agent.role_type for agent in active_agents} == expected_roles
        assert all(agent.enabled for agent in active_agents)


def test_overlay_panels_are_implemented_with_active_agents(context) -> None:
    expected_roles = {"specialist", "skeptic", "durability", "judge", "lead"}

    for panel_id in EXPECTED_WAVE4_PANEL_IDS:
        panel = context.get_panel(panel_id)
        active_agents = context.active_agents_for_panel(panel_id)

        assert panel.implemented is True
        assert panel.prompt_path.endswith("panel_lead.md")
        assert {agent.role_type for agent in active_agents} == expected_roles
        assert all(agent.enabled for agent in active_agents)


def test_expectations_rollout_policy_runs_after_company_quality(context) -> None:
    run_policies = context.registries.run_policies.run_policies

    assert run_policies["expectations_rollout"].wave == 3
    assert run_policies["expectations_rollout"].default_panel_ids == [
        "gatekeepers",
        "demand_revenue_quality",
        "supply_product_operations",
        "management_governance_capital_allocation",
        "financial_quality_liquidity_economic_model",
        "market_structure_growth",
        "macro_industry_transmission",
        "external_regulatory_geopolitical",
        "expectations_catalyst_realization",
    ]


def test_alembic_revision_ids_fit_default_version_table_limit() -> None:
    revision_ids: list[str] = []

    for path in sorted((Path(__file__).resolve().parents[1] / "alembic" / "versions").glob("*.py")):
        namespace: dict[str, object] = {}
        exec(path.read_text(), namespace)
        revision_ids.append(namespace["revision"])

    assert revision_ids
    assert all(len(revision) <= 32 for revision in revision_ids)


def test_wave2_tool_bundles_match_external_context_evidence_needs(context) -> None:
    bundles = {
        bundle.id: bundle for bundle in context.registries.tool_bundles.bundles
    }

    assert set(bundles["market_growth_research"].tool_ids) >= {
        "evidence_search",
        "claim_search",
        "filing_fetch",
        "transcript_fetch",
        "public_news_fetch",
        "financial_query",
    }
    assert set(bundles["macro_transmission_research"].tool_ids) >= {
        "evidence_search",
        "claim_search",
        "filing_fetch",
        "transcript_fetch",
        "public_news_fetch",
        "financial_query",
    }
    assert set(bundles["regulatory_context_research"].tool_ids) >= {
        "evidence_search",
        "claim_search",
        "filing_fetch",
        "transcript_fetch",
        "public_news_fetch",
    }


def test_expectations_tool_bundle_stays_bounded_to_expectation_inputs(context) -> None:
    bundles = {
        bundle.id: bundle for bundle in context.registries.tool_bundles.bundles
    }

    assert bundles["expectations_realization_research"].tool_ids == [
        "evidence_search",
        "claim_search",
        "estimate_revision_query",
        "event_calendar_query",
    ]


def test_overlay_tool_bundles_stay_bounded_to_overlay_inputs(context) -> None:
    bundles = {
        bundle.id: bundle for bundle in context.registries.tool_bundles.bundles
    }

    assert bundles["security_overlay_research"].tool_ids == [
        "evidence_search",
        "claim_search",
        "financial_query",
        "price_volume_query",
        "ownership_flow_query",
        "private_doc_fetch",
    ]
    assert bundles["portfolio_fit_research"].tool_ids == [
        "evidence_search",
        "claim_search",
        "portfolio_context_summary",
        "analog_lookup",
        "price_volume_query",
    ]


def test_phase6_removes_disabled_placeholder_leads_for_top_level_panels(context) -> None:
    placeholder_agents = [
        agent
        for agent in context.registries.agents.agents
        if agent.role_type == "lead"
        and not agent.enabled
        and agent.panel_id not in {None, "gatekeepers", "demand_revenue_quality"}
    ]

    assert placeholder_agents == []


def test_all_implemented_panels_reference_existing_prompts_and_owned_factors(
    context, repo_root
) -> None:
    implemented_panels = [
        panel for panel in context.registries.panels.panels if panel.id != "gatekeepers"
    ]
    factor_owner = {
        factor.id: factor.panel_id for factor in context.registries.factors.factors
    }

    for panel in implemented_panels:
        prompt_path = repo_root / panel.prompt_path
        assert prompt_path.is_file(), panel.prompt_path
        assert panel.factor_ids, panel.id
        assert all(factor_owner.get(factor_id) == panel.id for factor_id in panel.factor_ids), (
            panel.id
        )


def test_panels_expose_readiness_and_support_contracts(context) -> None:
    panels = {panel.id: panel for panel in context.registries.panels.panels}

    demand_panel = panels["demand_revenue_quality"]
    assert demand_panel.readiness.wave == 0
    assert demand_panel.support.required_company_types == ["public", "private"]
    assert demand_panel.support.weak_confidence.enabled is True
    assert demand_panel.readiness.required_evidence_families["private"] == [
        "core_company_documents",
        "dataroom",
        "kpi_reporting",
    ]

    expectations_panel = panels["expectations_catalyst_realization"]
    assert expectations_panel.readiness.required_context == []
    assert expectations_panel.support.weak_confidence.enabled is False

    security_overlay_panel = panels["security_or_deal_overlay"]
    assert security_overlay_panel.implemented is True
    assert security_overlay_panel.readiness.wave == 4
    assert security_overlay_panel.readiness.required_context == ["overlay_context"]
    assert security_overlay_panel.readiness.required_evidence_families["public"] == [
        "market_data",
        "security_context",
    ]
    assert security_overlay_panel.readiness.required_evidence_families["private"] == [
        "dataroom",
        "deal_context",
    ]
    assert security_overlay_panel.support.weak_confidence.enabled is False

    overlay_panel = panels["portfolio_fit_positioning"]
    assert overlay_panel.implemented is True
    assert overlay_panel.readiness.wave == 4
    assert overlay_panel.readiness.required_context == ["portfolio_context"]
    assert overlay_panel.support.weak_confidence.enabled is False

    supply_panel = panels["supply_product_operations"]
    assert supply_panel.implemented is True
    assert supply_panel.readiness.wave == 1
    assert supply_panel.readiness.minimum_evidence_count == 3

    management_panel = panels["management_governance_capital_allocation"]
    assert management_panel.implemented is True
    assert management_panel.readiness.minimum_evidence_count == 3

    financial_panel = panels["financial_quality_liquidity_economic_model"]
    assert financial_panel.implemented is True
    assert financial_panel.readiness.minimum_evidence_count == 3

    market_panel = panels["market_structure_growth"]
    assert market_panel.implemented is True
    assert market_panel.readiness.wave == 2
    assert market_panel.readiness.minimum_evidence_count == 5

    macro_panel = panels["macro_industry_transmission"]
    assert macro_panel.implemented is True
    assert macro_panel.readiness.wave == 2
    assert macro_panel.readiness.minimum_evidence_count == 4

    regulatory_panel = panels["external_regulatory_geopolitical"]
    assert regulatory_panel.implemented is True
    assert regulatory_panel.readiness.wave == 2
    assert regulatory_panel.readiness.minimum_evidence_count == 3


def test_registry_loader_rejects_invalid_cross_references(repo_root, tmp_path) -> None:
    config_dir = _copy_config(repo_root, tmp_path)
    panels_path = config_dir / "panels.yaml"
    panels = yaml.safe_load(panels_path.read_text(encoding="utf-8"))
    panels["panels"][0]["memo_section_ids"].append("missing_section")
    panels_path.write_text(yaml.safe_dump(panels, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="unknown memo sections"):
        RegistryLoader(config_dir, prompts_dir=repo_root / "prompts").load_all()


def test_registry_loader_rejects_missing_panel_support_evidence_family(repo_root, tmp_path) -> None:
    config_dir = _copy_config(repo_root, tmp_path)
    panels_path = config_dir / "panels.yaml"
    panels = yaml.safe_load(panels_path.read_text(encoding="utf-8"))
    panels["panels"][0]["readiness"]["required_evidence_families"].pop("private")
    panels_path.write_text(yaml.safe_dump(panels, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="missing required_evidence_families"):
        RegistryLoader(config_dir, prompts_dir=repo_root / "prompts").load_all()


def test_registry_loader_rejects_invalid_weak_confidence_thresholds(repo_root, tmp_path) -> None:
    config_dir = _copy_config(repo_root, tmp_path)
    panels_path = config_dir / "panels.yaml"
    panels = yaml.safe_load(panels_path.read_text(encoding="utf-8"))
    panels["panels"][1]["support"]["weak_confidence"]["minimum_factor_coverage_ratio"] = 0.9
    panels_path.write_text(yaml.safe_dump(panels, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="weak_confidence.minimum_factor_coverage_ratio"):
        RegistryLoader(config_dir, prompts_dir=repo_root / "prompts").load_all()


def test_registry_loader_rejects_invalid_cadence_policy_kind(repo_root, tmp_path) -> None:
    config_dir = _copy_config(repo_root, tmp_path)
    cadence_policies_path = config_dir / "cadence_policies.yaml"
    cadence_policies = yaml.safe_load(cadence_policies_path.read_text(encoding="utf-8"))
    cadence_policies["cadence_policies"][0]["kind"] = "hourly"
    cadence_policies_path.write_text(
        yaml.safe_dump(cadence_policies, sort_keys=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Unsupported cadence policy kind"):
        RegistryLoader(config_dir, prompts_dir=repo_root / "prompts").load_all()


def test_registry_loader_rejects_invalid_custom_weekday_sets(repo_root, tmp_path) -> None:
    config_dir = _copy_config(repo_root, tmp_path)
    cadence_policies_path = config_dir / "cadence_policies.yaml"
    cadence_policies = yaml.safe_load(cadence_policies_path.read_text(encoding="utf-8"))
    for policy in cadence_policies["cadence_policies"]:
        if policy["id"] == "custom_weekdays":
            policy["weekdays"] = ["monday", "monday"]
            break
    cadence_policies_path.write_text(
        yaml.safe_dump(cadence_policies, sort_keys=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unique weekdays"):
        RegistryLoader(config_dir, prompts_dir=repo_root / "prompts").load_all()


def test_registry_loader_rejects_unknown_cadence_policy_references(repo_root, tmp_path) -> None:
    config_dir = _copy_config(repo_root, tmp_path)
    run_policies_path = config_dir / "run_policies.yaml"
    run_policies = yaml.safe_load(run_policies_path.read_text(encoding="utf-8"))
    run_policies["run_policies"]["weekly_default"]["cadence"] = "unknown_policy"
    run_policies_path.write_text(
        yaml.safe_dump(run_policies, sort_keys=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unknown cadence policy"):
        RegistryLoader(config_dir, prompts_dir=repo_root / "prompts").load_all()


def test_registry_loader_rejects_run_policies_that_skip_gatekeepers(repo_root, tmp_path) -> None:
    config_dir = _copy_config(repo_root, tmp_path)
    run_policies_path = config_dir / "run_policies.yaml"
    run_policies = yaml.safe_load(run_policies_path.read_text(encoding="utf-8"))
    run_policies["run_policies"]["internal_company_quality"]["default_panel_ids"] = [
        "demand_revenue_quality"
    ]
    run_policies_path.write_text(
        yaml.safe_dump(run_policies, sort_keys=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="must begin with gatekeepers"):
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


def test_supply_management_financial_tool_bundles_are_least_privilege(context) -> None:
    bundles = {
        bundle.id: set(bundle.tool_ids) for bundle in context.registries.tool_bundles.bundles
    }

    assert bundles["supply_ops_research"] == {
        "evidence_search",
        "claim_search",
        "filing_fetch",
        "transcript_fetch",
        "private_doc_fetch",
    }
    assert bundles["management_research"] == {
        "evidence_search",
        "claim_search",
        "filing_fetch",
        "transcript_fetch",
        "public_news_fetch",
        "private_doc_fetch",
    }
    assert bundles["financial_quality_research"] == {
        "evidence_search",
        "claim_search",
        "filing_fetch",
        "private_doc_fetch",
        "financial_query",
        "spreadsheet_runner",
    }


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


def test_registry_loader_rejects_conflicting_legacy_and_explicit_connector_settings(
    repo_root, tmp_path
) -> None:
    config_dir = _copy_config(repo_root, tmp_path)
    source_connectors_path = config_dir / "source_connectors.yaml"
    source_connectors = yaml.safe_load(source_connectors_path.read_text(encoding="utf-8"))
    for connector in source_connectors["connectors"]:
        if connector["id"] == "public_file_connector":
            connector["settings"] = {
                "manifest_file": "alternate.json",
                "raw_landing_zone": connector["raw_landing_zone"],
            }
            break
    source_connectors_path.write_text(
        yaml.safe_dump(source_connectors, sort_keys=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="manifest_file must match"):
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
