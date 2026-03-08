from __future__ import annotations

from typing import Any

from ai_investing.config.models import AgentConfig, RegistryBundle, ToolDefinition
from ai_investing.domain.models import ToolInvocationLog
from ai_investing.persistence.repositories import Repository
from ai_investing.tools import builtins
from ai_investing.tools.base import ToolContext, ToolHandler
from ai_investing.tools.mcp import MCPAdapter


class ToolRegistryService:
    def __init__(self, registries: RegistryBundle):
        self._tool_definitions = {tool.id: tool for tool in registries.tool_registry.tools}
        self._bundles = {bundle.id: bundle.tool_ids for bundle in registries.tool_bundles.bundles}
        self._mcp = MCPAdapter(server_name="stub")
        self._builtin_handlers: dict[str, ToolHandler] = {
            "evidence_search": builtins.evidence_search,
            "claim_search": builtins.claim_search,
            "contradiction_finder": builtins.contradiction_finder,
            "analog_lookup": builtins.analog_lookup,
            "memo_section_writer": builtins.memo_section_writer,
            "public_doc_fetch": builtins.public_doc_fetch,
            "private_doc_fetch": builtins.private_doc_fetch,
            "passthrough_stub": builtins.passthrough_stub,
        }

    def allowed_tools_for_agent(self, agent: AgentConfig) -> set[str]:
        return set(self._bundles.get(agent.allowed_tool_bundle, []))

    def execute(
        self,
        *,
        repository: Repository,
        agent: AgentConfig,
        company_id: str,
        run_id: str,
        tool_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        allowed = self.allowed_tools_for_agent(agent)
        if tool_id not in allowed:
            raise PermissionError(f"{tool_id} is not allowed for bundle {agent.allowed_tool_bundle}")

        definition = self._tool_definitions[tool_id]
        result = self._execute_tool(
            definition=definition,
            context=ToolContext(
                company_id=company_id,
                run_id=run_id,
                agent_id=agent.id,
                repository=repository,
            ),
            payload=payload,
        )
        repository.save_tool_log(
            ToolInvocationLog(
                run_id=run_id,
                agent_id=agent.id,
                tool_id=tool_id,
                input_summary=str(payload),
                output_refs=[tool_id],
            )
        )
        return result

    def _execute_tool(
        self, *, definition: ToolDefinition, context: ToolContext, payload: dict[str, Any]
    ) -> dict[str, Any]:
        handler = self._builtin_handlers.get(definition.handler)
        if handler is not None:
            return handler(context, payload)
        return self._mcp.execute(definition.id, payload)

