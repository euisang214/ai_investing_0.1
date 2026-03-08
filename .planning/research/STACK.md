# Stack Research

## Recommended Stack

| Layer | Choice | Why |
|------|--------|-----|
| Language | Python 3.11+ | Good ecosystem support for LangGraph, FastAPI, Pydantic v2, and async I/O when needed |
| Package manager | `uv` | Fast project/environment management with straightforward lockfile support |
| API | FastAPI | Strong typing, OpenAPI generation, and easy dependency injection |
| CLI | Typer | Natural complement to FastAPI for operator workflows |
| Orchestration | LangGraph | Explicit graph composition for reusable subgraphs and long-lived state |
| Provider abstraction | LangChain wrappers only where useful | Keeps model adapters modular without coupling domain logic to a provider |
| Persistence | Postgres + SQLAlchemy 2.x | Strong relational indexes with JSON payload flexibility for typed memory artifacts |
| Testing | pytest | Broad ecosystem support and simple fixtures |
| Quality | Ruff + mypy | Fast linting and typed code discipline |
| Local dev | Docker Compose | Reliable Postgres-backed local environment and reproducible runs |

## What Not To Use

- Heavy inheritance-based domain frameworks — the architecture needs transparent composition and testability.
- n8n as the main reasoning runtime — it should stay outside the LangGraph service boundary.
- A frontend-first monolith — backend contracts should stabilize before UX work.

## Confidence

- Python/FastAPI/Postgres/LangGraph stack fit: High
- SQLAlchemy over bespoke persistence layer: High
- `uv` for developer workflow: Medium
