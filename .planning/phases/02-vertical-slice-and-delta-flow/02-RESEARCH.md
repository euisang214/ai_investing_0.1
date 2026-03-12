# Phase 2 Research: Vertical Slice And Delta Flow

## Repo-Specific Fit

Phase 2 should not invent a second runtime. The repo already has the right skeleton: config-driven panel selection, reusable LangGraph subgraphs, typed Pydantic records, SQLAlchemy persistence, Typer/FastAPI entrypoints, and a fake-provider test harness. The missing piece is first-class checkpointed execution after `gatekeepers`, plus explicit partial-memo and rerun-delta semantics.

Use the current `StateGraph` approach and extend it. Do not add a bespoke pause/resume service outside the graph. Add one checkpoint subgraph after the `gatekeepers` memo update, keep business artifacts in the existing domain tables, and use LangGraph persistence only for execution state.

Recommended implementation baseline:

- Compile `CompanyRefreshGraph` with a persistent LangGraph checkpointer backed by Postgres. Use one `run_id` per graph thread via `configurable.thread_id`. Confidence: High.
- Insert a `gatekeeper_checkpoint` node/subgraph after `gatekeepers` and before `demand_revenue_quality`. The node should call `interrupt()` and resume with `Command(resume=...)`. Confidence: High.
- Add first-class run lifecycle states for paused/gated/provisional outcomes and make them queryable through CLI/API. Do not encode checkpoint state only in free-form strings or opaque metadata. Confidence: High.
- Keep domain memory and graph execution memory separate. Claims, verdicts, memo sections, memo updates, memo snapshots, and monitoring deltas stay in the app database; LangGraph checkpoints track only execution position and resumable state. Confidence: High.
- Keep delta logic domain-specific. Compare structured claim/verdict/section records and materiality thresholds; do not make memo text diff the source of truth. Confidence: High.
- Refactor transaction scope before adding checkpoint/resume. Current service flow keeps one DB session around graph execution; for a pause-and-resume architecture, use smaller explicit transaction boundaries around durable writes. This is an inference from SQLAlchemy transaction scoping plus LangGraph durable execution requirements. Confidence: Medium.

## Standard Stack

Use this stack for Phase 2. It matches the current repo and the production pattern in current official docs.

| Area | Use | Why | Confidence |
| --- | --- | --- | --- |
| Graph runtime | `langgraph` `StateGraph`, subgraphs, `Command`, `interrupt`, `RetryPolicy` | This is the documented LangGraph production path for branching, human approval, retries, and resumable execution. | High |
| Graph checkpoint persistence | `langgraph-checkpoint-postgres` with `PostgresSaver` | Official docs say production checkpointers should be database-backed and show Postgres as the standard implementation. | High |
| Domain persistence | existing `SQLAlchemy 2` + `psycopg` + `Alembic` | Keep structured business memory in relational tables with reviewed migrations. | High |
| Contract layer | existing `Pydantic v2` models | Use strict typed models for new run/checkpoint response contracts, memo section status values, and delta records. | High |
| API surface | existing `FastAPI` with typed response models | FastAPI can validate, serialize, and filter response payloads, which is exactly what checkpoint-aware API contracts need. | High |
| CLI surface | existing `Typer` subcommands | Add explicit `continue-run` and `override-gatekeeper` commands instead of hiding control flow in ad hoc prompts. | Medium |
| Test stack | existing `pytest` fake-provider flow plus new checkpoint/resume integration tests | Phase 2 needs deterministic tests for stop, continue, provisional continue, rerun delta, and stale memo posture. | High |
| Optional, not required now | `PostgresStore` only if future phases need graph-native long-term memory beyond current domain tables | LangGraph separates thread-level checkpointing from long-term store memory; this phase only needs the checkpointer. | Medium |

Concrete package implication: keep the current `pyproject.toml` stack and add `langgraph-checkpoint-postgres`. Do not change orchestration frameworks.

## Architecture Patterns

1. One run equals one LangGraph thread.
Use `RunRecord.run_id` as the LangGraph `thread_id`. `analyze`, `refresh`, and `continue` should all invoke the same compiled graph with the same `thread_id` until the run reaches a terminal state. This matches LangGraph’s documented thread/checkpoint model. Confidence: High.

2. Checkpoint as a graph node, not a service-layer branch.
Run `gatekeepers`, persist its verdict and partial memo, then enter a dedicated checkpoint node that surfaces a structured interrupt payload with `gate_decision`, `awaiting_continue`, allowed actions, and provisional rules. Resume by passing `Command(resume=...)` back into the graph. Do not bolt resume logic onto CLI/API handlers while leaving the graph linear. Confidence: High.

3. Dual persistence: graph state for execution, domain tables for business artifacts.
LangGraph checkpoints should store resumable execution state. The app database should remain the source of truth for claims, verdicts, memo sections, memo updates, memo snapshots, monitoring deltas, and operator-visible run status. This separation is explicit in LangGraph docs, which distinguish checkpoint persistence from long-term store memory. Confidence: High.

4. Append-only memo projection.
Keep writing `MemoSectionUpdate` records and memo snapshots as projections. For every run, always emit the full memo section set. Add a `not_advanced` section status and keep `refreshed` and `stale`. The projection rule should be:

- updated this run -> `refreshed`
- not updated this run but exists from prior active memo -> `stale`
- never updated in any run -> `not_advanced`

`what_changed_since_last_run` is the exception: refresh it on every rerun, even when nothing material changed. Confidence: High.

5. Materiality comparator over structured records.
Treat deltas as a domain comparator, not a generic text diff. At minimum, compare claim meaning fields, confidence drift, stale-evidence state, affected memo sections, gate decision, and overall recommendation. Enforce the phase rule that confidence drift below `0.05` is immaterial by itself. Keep thresholds and drift-flag mappings in config, not in service conditionals. Confidence: High.

6. Provisional downstream analysis is a typed state, not a prose warning.
If a failed gatekeeper is explicitly overridden, mark the resumed run state as provisional and carry that flag into downstream verdicts, memo sections, and the final recommendation summary. Do not rely on prompt wording alone to preserve the distinction. Confidence: High.

7. Small transaction boundaries around durable writes.
The repo currently keeps one session open while graph execution proceeds. For checkpoint/resume, persist each durable artifact boundary explicitly: run created, gatekeeper verdict saved, partial memo saved, checkpoint status saved, resumed action saved, final memo saved, delta saved. This is an inference from SQLAlchemy transaction scoping plus LangGraph durable execution and is the safest fit for paused runs. Confidence: Medium.

8. Retry transient failures at the node level.
Use LangGraph `RetryPolicy` on nodes that perform model calls, connector fetches, or external tool I/O. Let user-fixable states pause with `interrupt()`. Let unexpected errors fail the run and be queryable. This matches the current LangGraph guidance for retries versus human input. Confidence: High.

## SOTA vs Current Practice

SOTA for LangGraph-style agent systems is durable, interruptible execution with persistent checkpoints, explicit thread identity, resumable human approval, retry policies, and idempotent side effects. Current official LangGraph docs are already aligned with that direction.

For this repo, the correct move is not to chase a new runtime or a platform rewrite. The right Phase 2 implementation is the current documented production pattern:

- `StateGraph` plus reusable subgraphs
- persistent Postgres-backed checkpointer
- `interrupt()` for gatekeeper pause
- `Command(resume=...)` for continue/override
- typed domain persistence for memo and delta artifacts
- config-driven drift thresholds and tool permissions

What to defer:

- `Agent Server` or LangGraph platform/server adoption. Official docs note that server products can hide checkpoint plumbing, but this repo already has its own CLI/API/service layer. Not needed for this phase. Confidence: Medium.
- `PostgresStore` or semantic memory search. Useful later if graph-native long-term memory becomes important, but redundant for a phase whose core requirement is structured memo history in domain tables. Confidence: Medium.
- Generalized multi-agent handoff abstractions beyond the current `gatekeeper` and `debate` subgraphs. Phase 2 should prove the slice, not widen the runtime surface. Confidence: High.

## Don't Hand-Roll

- Do not hand-roll pause/resume mechanics. Use LangGraph `interrupt()` and `Command(resume=...)` with a real checkpointer. Confidence: High.
- Do not hand-roll checkpoint persistence or resume tokens. Use `PostgresSaver` and LangGraph thread IDs. Confidence: High.
- Do not hand-roll a second memory system for graph execution. Use LangGraph checkpoints for runtime state and the existing SQLAlchemy models for domain memory. Confidence: High.
- Do not hand-roll migration management. Use Alembic revisions, ideally with autogenerate plus human review. Confidence: High.
- Do not hand-roll API contract filtering or serialization. Use explicit Pydantic response models in FastAPI so paused-run payloads are validated and filtered. Confidence: High.
- Do not hand-roll tool permission checks inside agents or prompts. Keep enforcement in the tool registry and bundles. Confidence: High.
- Do not hand-roll memo text diff as the primary delta engine. Generate prose from structured claim/verdict/section comparisons instead. This is a repo-specific recommendation, not a library claim. Confidence: High.

## Common Pitfalls

- Forgetting to compile the graph with a persistent checkpointer or forgetting to pass a stable `thread_id`. Result: `interrupt()` cannot give you a real stop-and-resume workflow. Confidence: High.
- Putting non-idempotent side effects before `interrupt()` or outside durable task boundaries. Result: duplicate writes or duplicate external calls when resuming after a failure or pause. Confidence: High.
- Wrapping `interrupt()` in try/except or reordering multiple interrupts inside a node. LangGraph explicitly warns against this. Confidence: High.
- Using graph checkpoints as the business record for paused runs. Result: CLI/API cannot query paused state, memo history, or provisional status without decoding runtime internals. Confidence: High.
- Returning only prose like “gatekeeper passed, continue?” from CLI/API. Result: no stable contract for automation, tests, or API clients. Return typed fields such as `awaiting_continue`, `gate_decision`, `gated_out`, `stopped_after_panel`, and `provisional`. Confidence: High.
- Rebuilding untouched memo sections as generic filler on every partial run. Result: operators cannot distinguish refreshed, stale, and never-advanced sections. Confidence: High.
- Treating confidence drift under `0.05` as material by itself. Result: noisy deltas that swamp real thesis movement. Confidence: High.
- Leaving drift flags and alert thresholds hardcoded in services. Result: Phase 3+ factor changes force runtime edits instead of config edits. Confidence: High.
- Holding a single long DB transaction around LLM/tool work and checkpoint pauses. Result: awkward rollback semantics and partial-write ambiguity on failure. This is an inference from SQLAlchemy session behavior and current repo flow. Confidence: Medium.
- Reusing `run-panel` as the gatekeeper-stop operator path without changing its semantics. The current path still reconciles memo and monitoring, so it is not a true checkpoint-only command. Confidence: High.

## Code Examples

### 1. Compile the graph with a Postgres checkpointer and use `run_id` as `thread_id`

```python
from langgraph.checkpoint.postgres import PostgresSaver


DB_URI = settings.langgraph_checkpoint_url

with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
    # Call setup() once during environment/bootstrap initialization.
    builder = build_company_refresh_graph_builder(...)
    graph = builder.compile(checkpointer=checkpointer)

    config = {"configurable": {"thread_id": run.run_id}}
    result = graph.invoke(
        {"company_id": company_id, "run_id": run.run_id, "panel_ids": selected_panels},
        config=config,
    )
```

Use one thread per run. Do not invent a separate resume token if `run_id` already exists.
If the current helper returns a compiled graph, refactor it so the checkpointer can be injected at compile time.

### 2. Implement the gatekeeper pause inside the graph

```python
from typing import Literal

from langgraph.types import Command, interrupt


def gatekeeper_checkpoint(state: RefreshState) -> Command[Literal["panel__demand_revenue_quality", "monitoring"]]:
    payload = {
        "run_id": state["run_id"],
        "gate_decision": state["gate_decision"],
        "awaiting_continue": True,
        "allowed_actions": ["stop", "continue", "continue_provisional"],
        "provisional_required": state["gate_decision"] == "fail",
    }
    resume_value = interrupt(payload)

    action = resume_value["action"]
    update = {
        "awaiting_continue": False,
        "checkpoint_action": action,
        "provisional": action == "continue_provisional",
    }

    if action == "stop":
        return Command(update={**update, "stopped_after_panel": "gatekeepers"}, goto="monitoring")

    return Command(update=update, goto="panel__demand_revenue_quality")
```

Resume from CLI/API with:

```python
result = graph.invoke(
    Command(resume={"action": "continue"}),
    config={"configurable": {"thread_id": run_id}},
)
```

This keeps the checkpoint in the graph, not in a parallel service workflow.

### 3. Keep delta logic domain-specific and materiality-aware

```python
def classify_claim_change(prior: ClaimCard, current: ClaimCard) -> bool:
    meaning_changed = any(
        [
            prior.claim != current.claim,
            prior.bull_case != current.bull_case,
            prior.bear_case != current.bear_case,
            prior.staleness_assessment != current.staleness_assessment,
        ]
    )
    confidence_changed = abs(prior.confidence - current.confidence) >= 0.05
    return meaning_changed or confidence_changed
```

Use this structured comparator first, then generate `what_changed_since_last_run` prose from the changed records.

### 4. Build partial memos as projections, not as ad hoc reports

```python
def project_section(section_id: str, current_update: MemoSection | None, prior_section: MemoSection | None) -> MemoSection:
    if current_update is not None:
        return current_update.model_copy(update={"status": MemoSectionStatus.REFRESHED})
    if prior_section is not None:
        return prior_section.model_copy(update={"status": MemoSectionStatus.STALE})
    return MemoSection(
        section_id=section_id,
        label=labels[section_id],
        content="This section has not been advanced yet.",
        status=MemoSectionStatus.NOT_ADVANCED,
    )
```

This is the simplest way to preserve the full memo contract across stopped and rerun states.

## Sources

Critical checkpoint/resume claims were cross-checked against multiple official LangGraph sources:

- [LangGraph Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)
- [LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- [LangGraph Durable Execution](https://docs.langchain.com/oss/python/langgraph/durable-execution)
- [LangGraph Add Memory](https://docs.langchain.com/oss/python/langgraph/add-memory)
- [LangGraph Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)
- [Thinking in LangGraph](https://docs.langchain.com/oss/python/langgraph/thinking-in-langgraph)

Supporting stack guidance:

- [FastAPI Response Models](https://fastapi.tiangolo.com/tutorial/response-model/)
- [Pydantic Models and Validation](https://docs.pydantic.dev/latest/concepts/models/)
- [Alembic Autogenerate](https://alembic.sqlalchemy.org/en/latest/autogenerate.html)
- [SQLAlchemy Session Transactions](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html)
