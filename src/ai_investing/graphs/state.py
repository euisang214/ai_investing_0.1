from __future__ import annotations

from typing import Any, TypedDict


class RefreshState(TypedDict, total=False):
    company_id: str
    run_id: str
    panel_ids: list[str]
    panel_results: dict[str, dict[str, Any]]
    memo: dict[str, Any]
    delta: dict[str, Any]

