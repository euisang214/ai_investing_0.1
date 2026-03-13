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
        self._monitoring_config = registries.monitoring.monitoring.model_dump(mode="python")
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
        self._validate_registry()

    def allowed_tools_for_agent(self, agent: AgentConfig) -> set[str]:
        if agent.allowed_tool_bundle not in self._bundles:
            raise KeyError(f"Unknown tool bundle: {agent.allowed_tool_bundle}")
        return set(self._bundles[agent.allowed_tool_bundle])

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
            raise PermissionError(
                f"{tool_id} is not allowed for bundle {agent.allowed_tool_bundle}"
            )
        if tool_id not in self._tool_definitions:
            raise KeyError(f"Unknown tool definition: {tool_id}")

        definition = self._tool_definitions[tool_id]
        result = self._execute_tool(
            definition=definition,
            context=ToolContext(
                company_id=company_id,
                run_id=run_id,
                agent_id=agent.id,
                repository=repository,
                settings={"monitoring": self._monitoring_config},
            ),
            payload=payload,
        )
        repository.save_tool_log(
            ToolInvocationLog(
                run_id=run_id,
                agent_id=agent.id,
                tool_id=tool_id,
                input_summary=str(payload),
                output_refs=self._output_refs_for_result(result),
            )
        )
        return result

    def _execute_tool(
        self, *, definition: ToolDefinition, context: ToolContext, payload: dict[str, Any]
    ) -> dict[str, Any]:
        handler = self._builtin_handlers.get(definition.handler)
        if handler is not None:
            return handler(context, payload)
        if definition.kind == "builtin":
            raise KeyError(f"No builtin handler registered for {definition.handler}")
        return self._mcp.execute(definition.id, payload)

    @staticmethod
    def _output_refs_for_result(result: dict[str, Any]) -> list[str]:
        raw_refs = result.get("output_refs")
        if not isinstance(raw_refs, list):
            return []
        return [str(ref) for ref in raw_refs if str(ref)]

    def _validate_registry(self) -> None:
        for bundle_id, tool_ids in self._bundles.items():
            missing_tools = [
                tool_id for tool_id in tool_ids if tool_id not in self._tool_definitions
            ]
            if missing_tools:
                joined = ", ".join(sorted(missing_tools))
                raise ValueError(f"Tool bundle {bundle_id} references unknown tools: {joined}")

        for tool in self._tool_definitions.values():
            if tool.kind == "builtin" and tool.handler not in self._builtin_handlers:
                raise ValueError(
                    f"Builtin tool {tool.id} references unknown handler {tool.handler}"
                )
