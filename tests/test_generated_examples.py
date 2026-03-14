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


def test_generation_script_writes_phase5_lifecycle_examples(
    repo_root: Path, tmp_path: Path
) -> None:
    output_root = tmp_path / "generated" / "ACME"

    _run_generator(repo_root, output_root)

    for stage in ("initial", "continued", "rerun"):
        stage_dir = output_root / stage
        assert stage_dir.is_dir()
        assert (stage_dir / "result.json").is_file()
        assert (stage_dir / "memo.md").is_file()
        assert (stage_dir / "delta.json").is_file()

    initial = _load_json(output_root / "initial" / "result.json")
    continued = _load_json(output_root / "continued" / "result.json")
    rerun = _load_json(output_root / "rerun" / "result.json")

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
    assert rerun["run"]["run_kind"] == "refresh"
    assert rerun["run"]["awaiting_continue"] is False
    assert rerun["delta"]["prior_run_id"] == continued["run"]["run_id"]
    assert "what_changed_since_last_run" in rerun["delta"]["changed_sections"]


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
    ):
        assert (checked_in_root / relative_path).read_text(encoding="utf-8") == (
            output_root / relative_path
        ).read_text(encoding="utf-8")


def test_checked_in_examples_describe_the_phase5_lifecycle(repo_root: Path) -> None:
    generated_root = repo_root / "examples" / "generated"
    readme = (generated_root / "README.md").read_text(encoding="utf-8")
    initial = _load_json(generated_root / "ACME" / "initial" / "result.json")
    continued = _load_json(generated_root / "ACME" / "continued" / "result.json")
    rerun = _load_json(generated_root / "ACME" / "rerun" / "result.json")
    initial_delta = _load_json(generated_root / "ACME" / "initial" / "delta.json")
    continued_delta = _load_json(generated_root / "ACME" / "continued" / "delta.json")
    rerun_delta = _load_json(generated_root / "ACME" / "rerun" / "delta.json")

    assert "python scripts/generate_phase2_examples.py" in readme
    assert "post-Phase-5 contract" in readme
    assert "auto-continue into downstream work" in readme
    assert "operator-only provisional override" in readme
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
    initial_memo = (generated_root / "ACME" / "initial" / "memo.md").read_text(encoding="utf-8")
    continued_memo = (generated_root / "ACME" / "continued" / "memo.md").read_text(
        encoding="utf-8"
    )
    rerun_memo = (generated_root / "ACME" / "rerun" / "memo.md").read_text(encoding="utf-8")

    assert initial_memo
    assert "Stale from the prior active memo." not in continued_memo
    assert "This section has not been advanced yet." in continued_memo
    assert "Stale from the prior active memo." in rerun_memo


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
