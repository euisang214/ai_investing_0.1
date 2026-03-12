from __future__ import annotations

import re
from pathlib import Path

import yaml

IMPLEMENTED_PANEL_IDS = {"gatekeepers", "demand_revenue_quality"}
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


def test_scaffold_prompts_follow_required_structure() -> None:
    for panel in _scaffold_panels():
        prompt_text = (_repo_root() / panel["prompt_path"]).read_text(encoding="utf-8")
        lower_text = prompt_text.lower()

        for heading in REQUIRED_HEADINGS:
            assert f"## {heading}" in prompt_text, (panel["id"], heading)

        assert "scaffold-only" in lower_text, panel["id"]
        assert "panelverdict" in lower_text, panel["id"]


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
