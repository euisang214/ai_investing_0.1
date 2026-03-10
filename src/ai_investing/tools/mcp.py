from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class MCPAdapter:
    server_name: str

    def execute(self, tool_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "status": "mcp_stub",
            "server_name": self.server_name,
            "tool_id": tool_id,
            "payload": payload,
        }
