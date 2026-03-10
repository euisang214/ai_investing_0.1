# Phase 1 Research: Foundation And Contracts

## Repo-Specific Assessment

This repository is already well into Phase 1. The core registry surface exists in `config/*.yaml`, typed config models exist in `src/ai_investing/config/models.py`, typed domain contracts exist in `src/ai_investing/domain/models.py`, repositories and tables exist in `src/ai_investing/persistence/`, provider wrappers exist in `src/ai_investing/providers/`, and the CLI/API/operator surface already exists in `src/ai_investing/cli.py` and `src/ai_investing/api/main.py`.

The implementation question is not "what stack should we start with?" It is "how do we harden the existing stack so future panels, memo updates, and weekly reruns do not force core runtime rewrites?"

The biggest Phase 1 theme is to move implicit runtime choices into registries and narrow adapters:

- keep YAML as the source of truth for topology
- keep Pydantic models as the contract boundary
- keep SQLAlchemy repositories as the persistence boundary
- keep provider wrappers thin and structured
- keep LangGraph composition declarative and reusable
- keep FastAPI and Typer as thin interface layers over shared services

## Standard Stack

| Layer | Use | Why |
| --- | --- | --- |
| Runtime | Python 3.11 | Matches the repo contract in `pyproject.toml`, keeps typing and library support straightforward, and avoids splitting the supported host story |
| Environment | Docker Compose as primary, `uv` as supported host workflow | Docker should stay the quick start; `uv` is a good host workflow once Python 3.11 is present |
| Config and settings | YAML registries + Pydantic v2 + `pydantic-settings` | Explicit files remain reviewable while validation stays strict and fail-fast |
| API | FastAPI with an app factory and `lifespan` | Keeps startup/shutdown scoped, testable, and aligned with current FastAPI guidance |
| CLI | Typer | Good fit for operator commands and shares the same typed domain/service layer as FastAPI |
| Orchestration | LangGraph compiled graphs and compiled subgraphs | Matches the requirement for reusable subgraphs and incremental memo updates |
| Persistence | SQLAlchemy 2 ORM + Postgres + Alembic | SQLAlchemy is already in place; Alembic should be added before more table churn lands |
| DB driver | `psycopg` 3 for Postgres | Already in the repo and the correct pairing with SQLAlchemy 2 |
| Structured outputs | LangChain only at the provider boundary via `with_structured_output(...)` | Keeps vendor SDK friction low without coupling domain logic to LangChain internals |
| Tests | `pytest` + fake provider + SQLite in-memory for fast tests, Postgres path for integration tests | Preserves the fake-provider requirement while keeping local feedback fast |
| Quality gates | `ruff` + `mypy --strict` | Already configured and appropriate for a contract-heavy backend |

Confidence:

- Stack fit for this repo: High
- Need for Alembic now, not later: High
- Need to shift FastAPI to app-factory/lifespan: High
- Need to make graph topology more registry-driven: High
- `uv` as the supported host workflow: Medium

## Architecture Patterns

1. Make panel orchestration config-driven all the way down.

The current repo already stores panel metadata in YAML, but `src/ai_investing/graphs/company_refresh.py` still hardcodes subgraph selection with:

- `gatekeeper` -> `build_gatekeeper_subgraph(...)`
- everything else -> `build_debate_subgraph(...)`

That is acceptable for the first slice but it will become a maintenance trap as more panel types arrive. Replace that conditional with a subgraph-builder registry keyed by `panel.subgraph`. The graph runtime should consume a declared subgraph type, not encode topology decisions inline.

2. Register compiled subgraphs as subgraphs instead of calling `subgraph.invoke({})` inside node wrappers.

LangGraph supports compiled subgraphs as first-class nodes. That is the better fit here because the system requirement is reusable subgraphs, not opaque helper calls. Calling `.invoke()` inside a node function hides internal graph structure, makes checkpointing less useful, and weakens future observability.

3. Keep the current "typed domain model -> repository row payload -> typed domain model" pattern.

The repo is already doing the right thing by keeping typed Pydantic contracts canonical and persisting JSON payloads plus query-critical columns. Continue this pattern. Add relational columns only for fields used for filtering, history selection, scheduling, and indexes. Do not move to prose-first storage.

4. Add Alembic before any more schema drift.

`Base.metadata.create_all(...)` is fine for early bootstrapping but not for a schema that is about to grow across claims, verdicts, memos, deltas, coverage, tool logs, and likely execution metadata. Phase 1 should end with a real migration path so future phases can evolve safely.

5. Convert FastAPI initialization to an app factory plus lifespan-managed context.

The current global `context = AppContext.load()` plus `@app.on_event("startup")` is simple, but it makes lifecycle control, test overrides, and future dependency injection harder. Move to:

- `create_app(settings: Settings | None = None) -> FastAPI`
- a `lifespan` function that loads context and initializes database resources
- request handlers that access `request.app.state.context`

6. Keep provider wrappers thin and deterministic.

The current provider adapters are directionally correct:

- shared `ModelProvider`
- optional provider extras
- structured output at the boundary
- fake provider for tests

Keep it that way. Do not let prompt assembly, retries, logging, or post-processing drift into the provider classes. Put those concerns in service or runtime helpers.

7. Keep memo storage structured and render views derived.

The repo already has `MemoSection`, `MemoSectionUpdate`, and `ICMemo`. Continue treating those as the source of truth. Markdown and JSON renderers should remain read models. This is critical for delta generation and weekly reruns.

8. Narrow registry mutation surface intentionally.

The phase context is correct: only `enable-agent`, `disable-agent`, and `reparent-agent` should be mutable through CLI/API right now. Everything else should remain file-driven YAML so diffs stay reviewable and topology changes stay deliberate.

9. Add a small runtime registry layer for "builder lookup" concerns.

Use registries for:

- subgraph builders by `panel.subgraph`
- output schema lookup by declared schema name
- tool handler lookup by tool definition
- provider selection by model profile

This keeps extension work inside config and lookup tables, not scattered conditionals.

10. Preserve two-tier local development support.

The repo and context both point to the correct posture:

- Docker-first quick start
- supported host workflow only when Python 3.11+ is present

Keep both paths documented, but keep Docker as the primary path to reduce environment drift.

## Don't Hand-Roll

- Database migrations. Use Alembic. Do not build an ad hoc migration runner around `create_all`.
- API lifecycle management. Use FastAPI lifespan and app factories. Do not build your own startup/shutdown convention.
- Environment/config loading. Use `pydantic-settings` plus validated YAML. Do not spread `os.getenv()` lookups across services.
- Graph persistence and resumability primitives. Use LangGraph's persistence/checkpoint model. Do not invent a parallel checkpoint format.
- Structured LLM output parsing. Use provider-level structured output into Pydantic models. Do not regex prose back into typed objects.
- CLI parsing and help generation. Use Typer. Do not build a custom command dispatcher.
- OpenAPI/request validation. Use FastAPI + Pydantic. Do not add hand-written request validation for normal endpoints.
- Registry inheritance systems. Keep registries explicit YAML with a few safe defaults. Do not introduce a custom templating DSL.
- Tool permission enforcement. Keep central bundle enforcement in the tool registry service. Do not let individual agents decide their own effective tool set.
- Memo and delta diffing semantics. Keep them in typed services and repositories. Do not move them into prompt-only behavior.

## Common Pitfalls

- Hidden topology in orchestration code. `company_refresh.py` still decides subgraph shape with inline Python conditionals; that will violate the config-driven rule as soon as another subgraph family appears.
- Opaque subgraph execution. Calling `.invoke()` inside nodes will make later checkpointing, tracing, and composition harder than necessary.
- Schema drift without migrations. The current database layer initializes tables but has no evolution path.
- Import-time app state. Global FastAPI context loading will make test isolation and runtime reload behavior brittle.
- Over-indexing JSON payloads. JSON payloads are fine for canonical storage, but every field that drives scheduling, history lookup, or filtering should have a projected relational column and index.
- Expanding CLI/API mutation power too early. Once APIs can edit broad registry state, config reviewability and runtime predictability degrade quickly.
- Placeholder expansion beyond panel metadata. Keep placeholders at the config/prompt level only; do not start emitting fake verdicts for not-yet-implemented panels.
- Blurring memo storage and memo rendering. The structured memo records must stay canonical or rerun deltas will become fragile.
- Letting provider adapters become orchestration layers. Providers should generate typed outputs, not decide business flow.
- Skipping Postgres-backed integration tests. SQLite is fine for speed, but at least one integration path should exercise the real Postgres runtime because the system is history- and JSON-heavy.

## Code Examples

### 1. Subgraph builder registry instead of inline conditionals

```python
from collections.abc import Callable

from langgraph.graph import END, StateGraph

SubgraphBuilder = Callable[[RefreshRuntime, str], object]


SUBGRAPH_BUILDERS: dict[str, SubgraphBuilder] = {
    "gatekeeper": build_gatekeeper_subgraph,
    "debate": build_debate_subgraph,
}


def build_company_refresh_graph(runtime: RefreshRuntime, panel_ids: list[str]):
    graph = StateGraph(RefreshState)
    previous_node: str | None = None

    for panel_id in panel_ids:
        panel = runtime.context.get_panel(panel_id)
        builder = SUBGRAPH_BUILDERS[panel.subgraph]
        panel_graph = builder(runtime, panel_id)
        panel_node = f"panel__{panel_id}"
        memo_node = f"memo__{panel_id}"

        graph.add_node(panel_node, panel_graph)
        graph.add_node(memo_node, partial(_memo_runner, runtime, panel_id))

        if previous_node is None:
            graph.set_entry_point(panel_node)
        else:
            graph.add_edge(previous_node, panel_node)

        graph.add_edge(panel_node, memo_node)
        previous_node = memo_node

    graph.add_node("monitoring", partial(_monitoring_runner, runtime))
    graph.add_node("ic_synthesis", partial(_ic_runner, runtime))
    graph.add_edge(previous_node or "monitoring", "monitoring")
    graph.add_edge("monitoring", "ic_synthesis")
    graph.add_edge("ic_synthesis", END)
    return graph.compile()
```

Why:

- keeps topology extensible
- lets LangGraph see actual subgraphs
- preserves the extension rule when new panel types arrive

### 2. FastAPI app factory with lifespan-managed context

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request


@asynccontextmanager
async def lifespan(app: FastAPI):
    context = AppContext.load()
    context.database.initialize()
    app.state.context = context
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="AI Investing", lifespan=lifespan)

    @app.get("/agents")
    def list_agents(request: Request) -> list[dict]:
        context = request.app.state.context
        return [
            agent.model_dump(mode="json")
            for agent in AgentConfigService(context).list_agents()
        ]

    return app
```

Why:

- matches current FastAPI guidance
- improves testability
- keeps initialization scoped and explicit

### 3. Repository pattern with projected columns plus canonical payload

```python
class ClaimCardRow(Base):
    __tablename__ = "claim_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    claim_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    company_id: Mapped[str] = mapped_column(String(64), index=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True)
    panel_id: Mapped[str] = mapped_column(String(64), index=True)
    factor_id: Mapped[str] = mapped_column(String(64), index=True)
    agent_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    namespace: Mapped[str] = mapped_column(String(255), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
```

Keep this pattern and extend it consistently:

- projected columns for query paths
- full payload for canonical typed reconstruction
- status transitions instead of destructive overwrite

### 4. Settings and registry loading kept centralized

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AI_INVESTING_", extra="ignore")

    database_url: str = "sqlite+pysqlite:///:memory:"
    config_dir: Path = Path("config")
    prompts_dir: Path = Path("prompts")
    provider: str = Field(default="fake")


class AppContext:
    @classmethod
    def load(cls, settings: Settings | None = None) -> "AppContext":
        resolved_settings = settings or Settings()
        registries = RegistryLoader(resolved_settings.config_dir).load_all()
        database = Database(resolved_settings.database_url)
        prompt_loader = PromptLoader(resolved_settings.prompts_dir)
        tool_registry = ToolRegistryService(registries)
        return cls(
            settings=resolved_settings,
            registries=registries,
            database=database,
            prompt_loader=prompt_loader,
            tool_registry=tool_registry,
        )
```

Why:

- one place to validate environment inputs
- one place to load YAML registries
- one place to rebuild runtime context after safe config edits

## Sources

- LangGraph overview: [https://docs.langchain.com/oss/python/langgraph/overview](https://docs.langchain.com/oss/python/langgraph/overview)
- LangGraph subgraphs: [https://docs.langchain.com/oss/python/langgraph/use-subgraphs](https://docs.langchain.com/oss/python/langgraph/use-subgraphs)
- LangGraph persistence: [https://docs.langchain.com/oss/python/langgraph/persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
- FastAPI lifespan events: [https://fastapi.tiangolo.com/advanced/events/](https://fastapi.tiangolo.com/advanced/events/)
- SQLAlchemy 2 declarative tables: [https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html](https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html)
- Alembic tutorial: [https://alembic.sqlalchemy.org/en/latest/tutorial.html](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- Pydantic settings usage: [https://docs.pydantic.dev/latest/concepts/pydantic_settings/](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- Typer docs: [https://typer.tiangolo.com/](https://typer.tiangolo.com/)
