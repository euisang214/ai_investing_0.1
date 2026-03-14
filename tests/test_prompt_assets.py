from __future__ import annotations

import re
from pathlib import Path

import yaml

IMPLEMENTED_PANEL_IDS = {
    "gatekeepers",
    "demand_revenue_quality",
    "supply_product_operations",
    "management_governance_capital_allocation",
    "financial_quality_liquidity_economic_model",
    "market_structure_growth",
    "macro_industry_transmission",
    "external_regulatory_geopolitical",
    "expectations_catalyst_realization",
    "security_or_deal_overlay",
    "portfolio_fit_positioning",
}
WAVE1_PRODUCTION_PROMPT_FILES = {
    "supply_product_operations": (
        "advocate.md",
        "skeptic.md",
        "durability.md",
        "judge.md",
        "panel_lead.md",
    ),
    "management_governance_capital_allocation": (
        "advocate.md",
        "skeptic.md",
        "durability.md",
        "judge.md",
        "panel_lead.md",
    ),
    "financial_quality_liquidity_economic_model": (
        "advocate.md",
        "skeptic.md",
        "durability.md",
        "judge.md",
        "panel_lead.md",
    ),
}
WAVE2_PRODUCTION_PROMPT_FILES = {
    "market_structure_growth": (
        "advocate.md",
        "skeptic.md",
        "durability.md",
        "judge.md",
        "panel_lead.md",
    ),
    "macro_industry_transmission": (
        "advocate.md",
        "skeptic.md",
        "durability.md",
        "judge.md",
        "panel_lead.md",
    ),
    "external_regulatory_geopolitical": (
        "advocate.md",
        "skeptic.md",
        "durability.md",
        "judge.md",
        "panel_lead.md",
    ),
}
WAVE3_PRODUCTION_PROMPT_FILES = {
    "expectations_catalyst_realization": (
        "advocate.md",
        "skeptic.md",
        "durability.md",
        "judge.md",
        "panel_lead.md",
    ),
}
WAVE4_PRODUCTION_PROMPT_FILES = {
    "security_or_deal_overlay": (
        "advocate.md",
        "skeptic.md",
        "durability.md",
        "judge.md",
        "panel_lead.md",
    ),
    "portfolio_fit_positioning": (
        "advocate.md",
        "skeptic.md",
        "durability.md",
        "judge.md",
        "panel_lead.md",
    ),
}
WAVE2_PANEL_LEAD_SECTIONS = (
    "Panel Purpose",
    "Affected Memo Sections",
    "Factor Coverage",
    "Evidence And Provenance Expectations",
    "Output Requirements",
)
WAVE3_PANEL_LEAD_SECTIONS = (
    "Panel Purpose",
    "Affected Memo Sections",
    "Factor Coverage",
    "Evidence And Provenance Expectations",
    "Output Requirements",
)
REQUIRED_HEADINGS = (
    "Panel Purpose",
    "Scaffold Status",
    "Output Contract",
    "Affected Memo Sections",
    "Factor Coverage",
    "Evidence And Provenance Expectations",
    "Future Implementation Handoff",
)
BANNED_FACTOR_PHRASES = {
    "placeholder factor",
    "generic factor",
    "factor to assess",
    "panel factor",
}
GENERIC_STOPWORDS = {
    "about",
    "after",
    "among",
    "before",
    "between",
    "could",
    "factor",
    "panel",
    "relevant",
    "their",
    "these",
    "through",
    "under",
    "until",
    "versus",
    "where",
    "while",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _scaffold_panels() -> list[dict]:
    panels = _load_yaml(_repo_root() / "config" / "panels.yaml")["panels"]
    return [panel for panel in panels if panel["id"] not in IMPLEMENTED_PANEL_IDS]


def _factor_map() -> dict[str, dict]:
    factors = _load_yaml(_repo_root() / "config" / "factors.yaml")["factors"]
    return {factor["id"]: factor for factor in factors}


def _panel_dir(panel_id: str) -> Path:
    repo_root = _repo_root()
    if panel_id == "management_governance_capital_allocation":
        return repo_root / "prompts" / "panels" / "management_governance"
    if panel_id == "financial_quality_liquidity_economic_model":
        return repo_root / "prompts" / "panels" / "financial_quality"
    if panel_id == "external_regulatory_geopolitical":
        return repo_root / "prompts" / "panels" / "external_regulatory"
    if panel_id == "security_or_deal_overlay":
        return repo_root / "prompts" / "panels" / "security_overlay"
    if panel_id == "portfolio_fit_positioning":
        return repo_root / "prompts" / "panels" / "portfolio_fit"
    return repo_root / "prompts" / "panels" / panel_id


def _section_block(text: str, heading: str) -> str:
    pattern = rf"^## {re.escape(heading)}\n(?P<body>.*?)(?=^## |\Z)"
    match = re.search(pattern, text, flags=re.MULTILINE | re.DOTALL)
    assert match, heading
    return match.group("body")


def _section_ids(text: str, heading: str) -> list[str]:
    return re.findall(r"- `([^`]+)`", _section_block(text, heading))


def _meaningful_tokens(factor: dict) -> list[str]:
    raw_tokens = factor["id"].lower().split("_")
    tokens = [token for token in raw_tokens if len(token) >= 4 and token not in GENERIC_STOPWORDS]
    if tokens:
        return tokens

    name_tokens = re.findall(r"[a-z]+", factor["name"].lower())
    return [token for token in name_tokens if len(token) >= 4 and token not in GENERIC_STOPWORDS]


def test_scaffold_prompt_inventory_is_complete() -> None:
    for panel in _scaffold_panels():
        prompt_path = _repo_root() / panel["prompt_path"]
        assert prompt_path.is_file(), panel["prompt_path"]


def test_supply_management_financial_prompt_inventory_is_complete() -> None:
    repo_root = _repo_root()

    for panel_id, filenames in WAVE1_PRODUCTION_PROMPT_FILES.items():
        if panel_id == "management_governance_capital_allocation":
            panel_dir = repo_root / "prompts" / "panels" / "management_governance"
        elif panel_id == "financial_quality_liquidity_economic_model":
            panel_dir = repo_root / "prompts" / "panels" / "financial_quality"
        else:
            panel_dir = repo_root / "prompts" / "panels" / panel_id

        for filename in filenames:
            assert (panel_dir / filename).is_file(), f"{panel_id}:{filename}"


def test_scaffold_prompts_follow_required_structure() -> None:
    for panel in _scaffold_panels():
        prompt_text = (_repo_root() / panel["prompt_path"]).read_text(encoding="utf-8")
        lower_text = prompt_text.lower()

        for heading in REQUIRED_HEADINGS:
            assert f"## {heading}" in prompt_text, (panel["id"], heading)

        assert "scaffold-only" in lower_text, panel["id"]
        assert "panelverdict" in lower_text, panel["id"]


def test_supply_management_financial_prompts_avoid_scaffold_language() -> None:
    repo_root = _repo_root()

    for panel_id, filenames in WAVE1_PRODUCTION_PROMPT_FILES.items():
        if panel_id == "management_governance_capital_allocation":
            panel_dir = repo_root / "prompts" / "panels" / "management_governance"
        elif panel_id == "financial_quality_liquidity_economic_model":
            panel_dir = repo_root / "prompts" / "panels" / "financial_quality"
        else:
            panel_dir = repo_root / "prompts" / "panels" / panel_id

        for filename in filenames:
            text = (panel_dir / filename).read_text(encoding="utf-8").lower()
            assert "scaffold-only" not in text, f"{panel_id}:{filename}"
            assert "placeholder" not in text, f"{panel_id}:{filename}"
            assert "weak-confidence" in text or "thin evidence" in text, f"{panel_id}:{filename}"


def test_market_macro_regulatory_prompt_inventory_is_complete() -> None:
    for panel_id, filenames in WAVE2_PRODUCTION_PROMPT_FILES.items():
        panel_dir = _panel_dir(panel_id)
        for filename in filenames:
            assert (panel_dir / filename).is_file(), f"{panel_id}:{filename}"


def test_market_macro_regulatory_prompts_avoid_scaffold_language() -> None:
    for panel_id, filenames in WAVE2_PRODUCTION_PROMPT_FILES.items():
        panel_dir = _panel_dir(panel_id)
        for filename in filenames:
            text = (panel_dir / filename).read_text(encoding="utf-8").lower()
            assert "scaffold-only" not in text, f"{panel_id}:{filename}"
            assert "placeholder" not in text, f"{panel_id}:{filename}"
            assert "weak-confidence" in text or "thin evidence" in text, f"{panel_id}:{filename}"


def test_market_macro_regulatory_panel_leads_encode_production_contract() -> None:
    panels = {
        panel["id"]: panel
        for panel in _load_yaml(_repo_root() / "config" / "panels.yaml")["panels"]
        if panel["id"] in WAVE2_PRODUCTION_PROMPT_FILES
    }

    for panel_id in WAVE2_PRODUCTION_PROMPT_FILES:
        lead_text = (_panel_dir(panel_id) / "panel_lead.md").read_text(encoding="utf-8")
        assert len(lead_text.splitlines()) >= 20, panel_id
        for heading in WAVE2_PANEL_LEAD_SECTIONS:
            assert f"## {heading}" in lead_text, (panel_id, heading)
        assert _section_ids(lead_text, "Affected Memo Sections") == panels[panel_id][
            "memo_section_ids"
        ]
        assert _section_ids(lead_text, "Factor Coverage") == panels[panel_id]["factor_ids"]


def test_expectations_prompt_inventory_is_complete() -> None:
    for panel_id, filenames in WAVE3_PRODUCTION_PROMPT_FILES.items():
        panel_dir = _panel_dir(panel_id)
        for filename in filenames:
            assert (panel_dir / filename).is_file(), f"{panel_id}:{filename}"


def test_expectations_prompts_avoid_scaffold_language() -> None:
    for panel_id, filenames in WAVE3_PRODUCTION_PROMPT_FILES.items():
        panel_dir = _panel_dir(panel_id)
        for filename in filenames:
            text = (panel_dir / filename).read_text(encoding="utf-8").lower()
            assert "scaffold-only" not in text, f"{panel_id}:{filename}"
            assert "placeholder" not in text, f"{panel_id}:{filename}"
            assert "thin evidence" in text, f"{panel_id}:{filename}"


def test_expectations_panel_lead_encodes_production_contract() -> None:
    panels = {
        panel["id"]: panel
        for panel in _load_yaml(_repo_root() / "config" / "panels.yaml")["panels"]
        if panel["id"] in WAVE3_PRODUCTION_PROMPT_FILES
    }

    for panel_id in WAVE3_PRODUCTION_PROMPT_FILES:
        lead_text = (_panel_dir(panel_id) / "panel_lead.md").read_text(encoding="utf-8")
        assert len(lead_text.splitlines()) >= 20, panel_id
        for heading in WAVE3_PANEL_LEAD_SECTIONS:
            assert f"## {heading}" in lead_text, (panel_id, heading)
        assert _section_ids(lead_text, "Affected Memo Sections") == panels[panel_id][
            "memo_section_ids"
        ]
        assert _section_ids(lead_text, "Factor Coverage") == panels[panel_id]["factor_ids"]


def test_overlay_prompt_inventory_is_complete() -> None:
    for panel_id, filenames in WAVE4_PRODUCTION_PROMPT_FILES.items():
        panel_dir = _panel_dir(panel_id)
        for filename in filenames:
            assert (panel_dir / filename).is_file(), f"{panel_id}:{filename}"


def test_overlay_prompts_avoid_scaffold_language() -> None:
    for panel_id, filenames in WAVE4_PRODUCTION_PROMPT_FILES.items():
        panel_dir = _panel_dir(panel_id)
        for filename in filenames:
            text = (panel_dir / filename).read_text(encoding="utf-8").lower()
            assert "scaffold-only" not in text, f"{panel_id}:{filename}"
            assert "placeholder" not in text, f"{panel_id}:{filename}"
            assert "thin evidence" in text, f"{panel_id}:{filename}"


def test_overlay_panel_leads_encode_production_contract() -> None:
    panels = {
        panel["id"]: panel
        for panel in _load_yaml(_repo_root() / "config" / "panels.yaml")["panels"]
        if panel["id"] in WAVE4_PRODUCTION_PROMPT_FILES
    }

    for panel_id in WAVE4_PRODUCTION_PROMPT_FILES:
        lead_text = (_panel_dir(panel_id) / "panel_lead.md").read_text(encoding="utf-8")
        assert len(lead_text.splitlines()) >= 20, panel_id
        for heading in WAVE3_PANEL_LEAD_SECTIONS:
            assert f"## {heading}" in lead_text, (panel_id, heading)
        assert _section_ids(lead_text, "Affected Memo Sections") == panels[panel_id][
            "memo_section_ids"
        ]
        assert _section_ids(lead_text, "Factor Coverage") == panels[panel_id]["factor_ids"]


def test_scaffold_prompt_sections_match_panel_config() -> None:
    factors = _factor_map()

    for panel in _scaffold_panels():
        prompt_text = (_repo_root() / panel["prompt_path"]).read_text(encoding="utf-8")
        memo_sections = _section_ids(prompt_text, "Affected Memo Sections")
        factor_ids = _section_ids(prompt_text, "Factor Coverage")

        assert memo_sections == panel["memo_section_ids"], panel["id"]
        assert factor_ids == panel["factor_ids"], panel["id"]
        assert all(factors[factor_id]["panel_id"] == panel["id"] for factor_id in factor_ids), (
            panel["id"]
        )


def test_scaffold_factor_descriptions_are_panel_specific() -> None:
    factors = _factor_map()

    for panel in _scaffold_panels():
        panel_descriptions: set[str] = set()
        for factor_id in panel["factor_ids"]:
            factor = factors[factor_id]
            description = " ".join(str(factor["description"]).lower().split())
            meaningful_tokens = _meaningful_tokens(factor)

            assert description not in BANNED_FACTOR_PHRASES, factor_id
            assert len(description) >= 24, factor_id
            if meaningful_tokens:
                assert any(token in description for token in meaningful_tokens), factor_id
            else:
                content_words = [
                    token
                    for token in re.findall(r"[a-z]+", description)
                    if len(token) >= 4 and token not in GENERIC_STOPWORDS
                ]
                assert len(content_words) >= 4, factor_id

            panel_descriptions.add(description)

        assert len(panel_descriptions) == len(panel["factor_ids"]), panel["id"]
