from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from ai_investing.persistence.repositories import Repository


@dataclass(slots=True)
class ToolContext:
    company_id: str
    run_id: str
    agent_id: str
    repository: Repository
    settings: dict[str, Any] = field(default_factory=dict)


ToolHandler = Callable[[ToolContext, dict[str, Any]], dict[str, Any]]
