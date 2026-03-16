# Phase 12: Cost Controls And CI/CD - Context

**Gathered:** 2026-03-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Give operators visibility into LLM costs (token usage, estimated USD, and active budget caps) and ensure code quality is automatically validated via CI/CD pipelines.

</domain>

<decisions>
## Implementation Decisions

### Budget Enforcement Behavior
- Graceful abort between graph steps: Instead of a hard crash mid-node, the graph should check accumulated token usage between steps (e.g., via a routing node or conditional edge) and route to a clean terminal state if `AI_INVESTING_MAX_TOKENS_PER_RUN` is blown.
- The run result should record this as the reason for abort.

### Rate Card Management
- A dedicated `rate_cards.yaml` configuration file will store the input and output USD cost per token for each supported model.
- This allows updates without code changes.

### CI/CD Execution Scope
- The GitHub Actions pipeline (`ci.yml`) should run on pushes to the `main` branch and on all Pull Requests. It will skip pushes to standalone branches until a PR is opened.

### Claude's Discretion
- **Budget Calculation Mechanism**: Decide the cleanest way to extract and accumulate token usage (e.g., reading `.response_metadata` from AIMessage vs. using isolated LangChain callbacks), prioritizing whatever works best with the LangGraph state.
- **State Payload**: Where and how `token_usage` is accumulated and stored in the graph state prior to finalizing the run result.
- **Config integration**: How `rate_cards.yaml` is loaded relative to the existing YAML parser tools.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Settings` class (`settings.py`): Place to add `AI_INVESTING_MAX_TOKENS_PER_RUN`.
- `RunRecord` / `RunResult` models: Need fields for `token_usage` (input, output, cost).
- `RegistryLoader`: Similar mechanisms can be used to load `rate_cards.yaml` if needed, or a simpler YAML read on startup.

### Established Patterns
- LangGraph compilation happens centrally or in subgraphs; conditional routing already exists (e.g., gatekeepers).
- The `fake` provider (`AI_INVESTING_PROVIDER=fake`) does not require API keys, making it perfect for CI checks.

### Integration Points
- Graph state definitions (`src/ai_investing/graphs/state.py` or similar) to hold running token sums.
- Node routers/edges (`src/ai_investing/graphs/`) to implement the graceful abort logic.
- `.github/workflows/ci.yml` (to be created) for CI operations.

</code_context>

<specifics>
## Specific Ideas

- None — open to standard approaches as long as the decisions are respected.

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope.

</deferred>

---

*Phase: 12-cost-controls-and-ci-cd*
*Context gathered: 2026-03-15*
