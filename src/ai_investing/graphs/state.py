from __future__ import annotations

from typing import Any, TypedDict


class RefreshState(TypedDict, total=False):
    company_id: str
    run_id: str
    panel_ids: list[str]
    panel_results: dict[str, dict[str, Any]]
    claims: list[dict[str, Any]]
    verdict: dict[str, Any]
    memo: dict[str, Any]
    delta: dict[str, Any]
    gate_decision: str
    awaiting_continue: bool
    gated_out: bool
    provisional: bool
    stopped_after_panel: str | None
    checkpoint_panel_id: str | None
    resume_action: str | None
