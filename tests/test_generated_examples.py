from __future__ import annotations

import importlib.util
import json
import sys
from collections import defaultdict
from pathlib import Path


def _run_generator(repo_root: Path, output_root: Path) -> None:
    module_path = repo_root / "scripts" / "generate_phase2_examples.py"
    spec = importlib.util.spec_from_file_location("generate_phase2_examples", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.generate_examples(output_root=output_root)


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _section_map(result: dict[str, object]) -> dict[str, dict[str, object]]:
    memo = result["memo"]
    assert isinstance(memo, dict)
    sections = memo["sections"]
    assert isinstance(sections, list)
    return {section["section_id"]: section for section in sections}


def test_generation_script_writes_phase6_runtime_examples(
    repo_root: Path, tmp_path: Path
) -> None:
    output_root = tmp_path / "generated" / "ACME"

    _run_generator(repo_root, output_root)

    for stage in ("initial", "continued", "rerun", "overlay_gap"):
        stage_dir = output_root / stage
        assert stage_dir.is_dir()
        assert (stage_dir / "result.json").is_file()
        assert (stage_dir / "memo.md").is_file()
        assert (stage_dir / "delta.json").is_file()

    initial = _load_json(output_root / "initial" / "result.json")
    continued = _load_json(output_root / "continued" / "result.json")
    rerun = _load_json(output_root / "rerun" / "result.json")
    overlay_gap = _load_json(output_root / "overlay_gap" / "result.json")

    assert initial["run"]["status"] == "complete"
    assert initial["run"]["gate_decision"] in {"pass", "review"}
    assert initial["run"]["awaiting_continue"] is False
    assert initial["run"]["checkpoint"]["resolution_action"] == "continue"
    assert "continue automatically" in initial["run"]["checkpoint"]["note"]
    assert initial["delta"]["prior_run_id"] is None
    assert continued["run"]["run_id"] == initial["run"]["run_id"]
    assert continued["run"]["status"] == "complete"
    assert continued["run"]["checkpoint"]["resolution_action"] == "continue"
    assert continued["memo"]["is_initial_coverage"] is True
    assert continued["delta"]["prior_run_id"] is None
    assert (
        initial["panels"]["expectations_catalyst_realization"]["support"]["status"]
        == "supported"
    )
    assert (
        continued["panels"]["expectations_catalyst_realization"]["support"]["status"]
        == "supported"
    )
    assert rerun["run"]["run_kind"] == "refresh"
    assert rerun["run"]["awaiting_continue"] is False
    assert rerun["delta"]["prior_run_id"] == continued["run"]["run_id"]
    assert "what_changed_since_last_run" in rerun["delta"]["changed_sections"]
    assert "expectations_variant_view" in rerun["delta"]["changed_sections"]
    assert "realization_path_catalysts" in rerun["delta"]["changed_sections"]
    assert _section_map(initial)["expectations_variant_view"]["status"] == "refreshed"
    assert _section_map(initial)["realization_path_catalysts"]["status"] == "refreshed"
    assert overlay_gap["run"]["metadata"]["panel_policy"] == "full_surface"
    assert overlay_gap["run"]["status"] == "complete"
    assert overlay_gap["panels"]["security_or_deal_overlay"]["support"]["status"] == "unsupported"
    assert overlay_gap["panels"]["portfolio_fit_positioning"]["support"]["status"] == "unsupported"
    assert overlay_gap["panels"]["security_or_deal_overlay"]["skip"]["reason_code"] == "missing_context"
    assert overlay_gap["panels"]["portfolio_fit_positioning"]["skip"]["reason_code"] == "missing_context"
    assert (
        _section_map(overlay_gap)["portfolio_fit_positioning"]["status"] == "not_advanced"
    )


def test_generated_expectations_delta_examples_include_rerun_changes(
    repo_root: Path, tmp_path: Path
) -> None:
    output_root = tmp_path / "generated" / "ACME"

    _run_generator(repo_root, output_root)

    initial = _load_json(output_root / "initial" / "result.json")
    rerun = _load_json(output_root / "rerun" / "result.json")

    assert (
        initial["panels"]["expectations_catalyst_realization"]["support"]["status"]
        == "supported"
    )
    assert _section_map(initial)["expectations_variant_view"]["status"] == "refreshed"
    assert _section_map(initial)["realization_path_catalysts"]["status"] == "refreshed"
    assert "expectations_variant_view" in rerun["delta"]["changed_sections"]
    assert "realization_path_catalysts" in rerun["delta"]["changed_sections"]


def test_checked_in_examples_match_generator_output(repo_root: Path, tmp_path: Path) -> None:
    output_root = tmp_path / "generated" / "ACME"
    checked_in_root = repo_root / "examples" / "generated" / "ACME"

    _run_generator(repo_root, output_root)

    for relative_path in (
        Path("initial/result.json"),
        Path("initial/memo.md"),
        Path("initial/delta.json"),
        Path("continued/result.json"),
        Path("continued/memo.md"),
        Path("continued/delta.json"),
        Path("rerun/result.json"),
        Path("rerun/memo.md"),
        Path("rerun/delta.json"),
        Path("overlay_gap/result.json"),
        Path("overlay_gap/memo.md"),
        Path("overlay_gap/delta.json"),
    ):
        assert (checked_in_root / relative_path).read_text(encoding="utf-8") == (
            output_root / relative_path
        ).read_text(encoding="utf-8")


def test_checked_in_examples_describe_the_phase6_runtime(repo_root: Path) -> None:
    generated_root = repo_root / "examples" / "generated"
    readme = (generated_root / "README.md").read_text(encoding="utf-8")
    initial = _load_json(generated_root / "ACME" / "initial" / "result.json")
    continued = _load_json(generated_root / "ACME" / "continued" / "result.json")
    rerun = _load_json(generated_root / "ACME" / "rerun" / "result.json")
    overlay_gap = _load_json(generated_root / "ACME" / "overlay_gap" / "result.json")
    initial_delta = _load_json(generated_root / "ACME" / "initial" / "delta.json")
    continued_delta = _load_json(generated_root / "ACME" / "continued" / "delta.json")
    rerun_delta = _load_json(generated_root / "ACME" / "rerun" / "delta.json")

    assert "python scripts/generate_phase2_examples.py" in readme
    assert "shipped Phase 6 runtime contract" in readme
    assert "full_surface" in readme
    assert "overlay_gap/" in readme
    assert "unsupported and skipped explicitly" in readme
    assert "initial/" in readme
    assert "continued/" in readme
    assert "rerun/" in readme
    assert initial["run"]["status"] == "complete"
    assert initial["run"]["awaiting_continue"] is False
    assert initial["run"]["checkpoint"]["resolution_action"] == "continue"
    assert initial_delta["prior_run_id"] is None
    assert continued["run"]["run_id"] == initial["run"]["run_id"]
    assert continued["run"]["metadata"]["baseline_memo"] is None
    assert continued["run"]["metadata"]["baseline_active_claims"] == []
    assert continued["run"]["metadata"]["baseline_active_verdicts"] == []
    assert continued["memo"]["is_initial_coverage"] is True
    assert continued_delta["current_run_id"] == continued["run"]["run_id"]
    assert continued_delta["prior_run_id"] is None
    assert rerun["run"]["run_kind"] == "refresh"
    assert rerun["run"]["checkpoint"]["resolution_action"] == "continue"
    assert rerun_delta["prior_run_id"] == continued["run"]["run_id"]
    assert overlay_gap["run"]["metadata"]["panel_policy"] == "full_surface"
    assert overlay_gap["panels"]["security_or_deal_overlay"]["support"]["status"] == "unsupported"
    assert overlay_gap["panels"]["portfolio_fit_positioning"]["support"]["status"] == "unsupported"
    assert overlay_gap["panels"]["security_or_deal_overlay"]["skip"]["reason_code"] == "missing_context"
    assert overlay_gap["panels"]["portfolio_fit_positioning"]["skip"]["reason_code"] == "missing_context"
    assert (
        initial["panels"]["expectations_catalyst_realization"]["support"]["status"]
        == "supported"
    )
    assert (
        rerun["panels"]["expectations_catalyst_realization"]["support"]["status"]
        == "supported"
    )
    assert "expectations_variant_view" in rerun_delta["changed_sections"]
    assert "realization_path_catalysts" in rerun_delta["changed_sections"]
    initial_memo = (generated_root / "ACME" / "initial" / "memo.md").read_text(encoding="utf-8")
    continued_memo = (generated_root / "ACME" / "continued" / "memo.md").read_text(
        encoding="utf-8"
    )
    rerun_memo = (generated_root / "ACME" / "rerun" / "memo.md").read_text(encoding="utf-8")
    overlay_gap_memo = (generated_root / "ACME" / "overlay_gap" / "memo.md").read_text(
        encoding="utf-8"
    )

    assert initial_memo
    assert "Stale from the prior active memo." not in continued_memo
    assert "This section has not been advanced yet." in continued_memo
    assert "Stale from the prior active memo." in rerun_memo
    assert "## Expectations And Variant View" in initial_memo
    assert "## Realization Path And Catalysts" in initial_memo
    assert "unsupported for this run" in overlay_gap_memo


def test_supply_management_financial_manifests_cover_wave1_public_and_private_samples(
    repo_root: Path,
) -> None:
    panel_ids = {
        "supply_product_operations",
        "management_governance_capital_allocation",
        "financial_quality_liquidity_economic_model",
    }
    allowed_wave1_factors = {
        "supply_side_advantage",
        "production_distribution_channels",
        "reliability",
        "input_pricing_availability",
        "innovation",
        "barriers_to_entry",
        "negotiating_power",
        "product_concentration",
        "procurement_supplier_concentration",
        "supplier_fiscal_health",
        "priorities",
        "capital_allocation",
        "ability_to_hit_projections",
        "management_team_per_member",
        "tenure",
        "planning_execution",
        "incentive_alignment",
        "org_legal_structure",
        "related_party_red_flags",
        "financial_audit",
        "earnings_quality",
        "business_model_cash_timing",
        "margin_profile_operating_leverage",
        "fiscal_health",
        "capitalization",
        "unit_economics",
        "capital_efficiency",
        "roic_decomposition",
        "incremental_roic_reinvestment_runway",
        "off_balance_sheet_liabilities_equity",
    }
    factor_counts: dict[str, set[str]] = defaultdict(set)

    for manifest_path in (
        repo_root / "examples" / "acme_public" / "manifest.json",
        repo_root / "examples" / "beta_private" / "manifest.json",
    ):
        manifest = _load_json(manifest_path)
        seen_panels = {
            panel_id
            for document in manifest["documents"]
            for panel_id in document["panel_ids"]
            if panel_id in panel_ids
        }
        assert seen_panels == panel_ids
        for document in manifest["documents"]:
            for panel_id in panel_ids.intersection(document["panel_ids"]):
                factor_counts[f"{manifest['company_id']}:{panel_id}"].update(
                    factor_id
                    for factor_id in document["factor_ids"]
                    if factor_id in allowed_wave1_factors
                )

    assert len(factor_counts["ACME:supply_product_operations"]) >= 5
    assert len(factor_counts["ACME:management_governance_capital_allocation"]) >= 8
    assert len(factor_counts["ACME:financial_quality_liquidity_economic_model"]) >= 8
    assert len(factor_counts["BETA:supply_product_operations"]) >= 4
    assert len(factor_counts["BETA:management_governance_capital_allocation"]) >= 5
    assert len(factor_counts["BETA:financial_quality_liquidity_economic_model"]) >= 6


def test_market_macro_regulatory_manifests_cover_wave2_public_and_private_samples(
    repo_root: Path,
) -> None:
    panel_ids = {
        "market_structure_growth",
        "macro_industry_transmission",
        "external_regulatory_geopolitical",
    }
    allowed_wave2_factors = {
        "industry_market_share_trends",
        "tam",
        "per_product_market_share_history",
        "industry_cagr_vs_revenue_cagr",
        "organic_vs_inorganic_growth",
        "growth_levers",
        "secular_vs_cyclical_growth",
        "adjacency_expansion_runway",
        "macro_variable_exposure",
        "transmission_mechanisms",
        "cycle_sensitivity",
        "value_chain_relationships",
        "budget_cycle_exposure",
        "regulation_subsidy_tax_transmission",
        "government_exposure",
        "geopolitical_exposure",
        "subsidies_taxes",
        "litigation_contingent_liabilities",
        "regulatory_dependency",
    }
    factor_counts: dict[str, set[str]] = defaultdict(set)

    for manifest_path in (
        repo_root / "examples" / "acme_public" / "manifest.json",
        repo_root / "examples" / "beta_private" / "manifest.json",
        repo_root / "examples" / "connectors" / "acme_market_packet" / "manifest.json",
        repo_root / "examples" / "connectors" / "acme_regulatory_packet" / "manifest.json",
        repo_root / "examples" / "connectors" / "acme_transcript_news_packet" / "manifest.json",
    ):
        manifest = _load_json(manifest_path)
        for document in manifest["documents"]:
            for panel_id in panel_ids.intersection(document["panel_ids"]):
                factor_counts[f"{manifest['company_id']}:{panel_id}"].update(
                    factor_id
                    for factor_id in document["factor_ids"]
                    if factor_id in allowed_wave2_factors
                )

    assert len(factor_counts["ACME:market_structure_growth"]) >= 6
    assert len(factor_counts["ACME:macro_industry_transmission"]) >= 5
    assert len(factor_counts["ACME:external_regulatory_geopolitical"]) >= 4
    assert len(factor_counts["BETA:market_structure_growth"]) >= 5
    assert len(factor_counts["BETA:macro_industry_transmission"]) >= 3
    assert len(factor_counts["BETA:external_regulatory_geopolitical"]) >= 3


def test_wave2_connector_packets_publish_explicit_external_context_provenance(
    repo_root: Path,
) -> None:
    market_manifest = _load_json(
        repo_root / "examples" / "connectors" / "acme_market_packet" / "manifest.json"
    )
    regulatory_manifest = _load_json(
        repo_root / "examples" / "connectors" / "acme_regulatory_packet" / "manifest.json"
    )
    transcript_manifest = _load_json(
        repo_root
        / "examples"
        / "connectors"
        / "acme_transcript_news_packet"
        / "manifest.json"
    )

    market_factors = {
        factor_id
        for document in market_manifest["documents"]
        for factor_id in document["factor_ids"]
        if "market_structure_growth" in document["panel_ids"]
        or "macro_industry_transmission" in document["panel_ids"]
    }
    regulatory_factors = {
        factor_id
        for document in regulatory_manifest["documents"]
        for factor_id in document["factor_ids"]
        if "external_regulatory_geopolitical" in document["panel_ids"]
    }
    transcript_factors = {
        factor_id
        for document in transcript_manifest["documents"]
        for factor_id in document["factor_ids"]
        if {
            "market_structure_growth",
            "macro_industry_transmission",
            "external_regulatory_geopolitical",
        }.intersection(document["panel_ids"])
    }

    assert {doc["metadata"]["evidence_family"] for doc in market_manifest["documents"]} == {
        "market"
    }
    assert {doc["metadata"]["evidence_family"] for doc in regulatory_manifest["documents"]} == {
        "regulatory"
    }
    assert {doc["metadata"]["evidence_family"] for doc in transcript_manifest["documents"]} == {
        "transcript",
        "news",
    }
    assert {
        "industry_market_share_trends",
        "industry_cagr_vs_revenue_cagr",
        "macro_variable_exposure",
        "transmission_mechanisms",
        "budget_cycle_exposure",
        "fx_rates_credit_exposure",
    }.issubset(market_factors)
    assert {
        "geopolitical_exposure",
        "subsidies_taxes",
        "regulatory_dependency",
        "litigation_contingent_liabilities",
    }.issubset(regulatory_factors)
    assert {
        "adjacency_expansion_runway",
        "per_product_market_share_history",
        "value_chain_relationships",
        "government_exposure",
        "regulatory_dependency",
    }.issubset(transcript_factors)


def test_expectations_manifests_cover_public_private_and_rerun_samples(repo_root: Path) -> None:
    panel_id = "expectations_catalyst_realization"
    expected_factors = {
        "implied_expectations",
        "consensus_narrative_map",
        "variant_view",
        "falsification_kill_criteria",
        "catalyst_path",
        "timing_path_dependency",
        "milestone_checklist",
    }

    public_connectors = (
        repo_root / "examples" / "connectors" / "acme_consensus_packet" / "manifest.json",
        repo_root / "examples" / "connectors" / "acme_events_packet" / "manifest.json",
    )
    private_manifest = repo_root / "examples" / "beta_private" / "manifest.json"
    rerun_manifest = repo_root / "examples" / "acme_public_rerun" / "manifest.json"

    public_factors: set[str] = set()
    public_families: set[str] = set()
    for manifest_path in public_connectors:
        manifest = _load_json(manifest_path)
        for document in manifest["documents"]:
            if panel_id in document["panel_ids"]:
                public_factors.update(
                    factor_id
                    for factor_id in document["factor_ids"]
                    if factor_id in expected_factors
                )
                public_families.add(document["metadata"]["evidence_family"])

    private_manifest_data = _load_json(private_manifest)
    private_factors = {
        factor_id
        for document in private_manifest_data["documents"]
        if panel_id in document["panel_ids"]
        for factor_id in document["factor_ids"]
        if factor_id in expected_factors
    }
    private_families = {
        document["metadata"]["evidence_family"]
        for document in private_manifest_data["documents"]
        if panel_id in document["panel_ids"]
    }

    rerun_manifest_data = _load_json(rerun_manifest)
    rerun_factors = {
        factor_id
        for document in rerun_manifest_data["documents"]
        if panel_id in document["panel_ids"]
        for factor_id in document["factor_ids"]
        if factor_id in expected_factors
    }

    assert public_factors == expected_factors
    assert {"consensus", "market", "events"} == public_families
    assert private_factors == expected_factors
    assert "events" in private_families
    assert {"variant_view", "timing_path_dependency", "falsification_kill_criteria"}.issubset(
        rerun_factors
    )
