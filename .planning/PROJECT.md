# AI Investing

## What This Is

AI Investing is a production-ready, config-driven multi-agent investment research platform for public and private company analysis. It ingests structured evidence, runs a configurable cohort of specialist and panel agents backed by real LLM providers, preserves factor-level memory over time, and maintains a living investment committee memo that updates section-by-section as analysis completes.

The system targets research teams that need repeatable weekly refreshes for watchlist and portfolio companies without hardcoding panel topology into orchestration logic. Deployment is Docker-based with API key authentication, role-based access control, health probes, and cost controls out of the box.

## Core Value

Produce a continuously updatable, auditable investment view where factor-level claims, panel verdicts, and memo deltas remain structured and reusable across reruns.

## Requirements

### Validated

- ✓ Config-driven multi-agent orchestration with all 11 top-level panels productionized — v1.0
- ✓ Typed persistence for evidence, claims, verdicts, memo snapshots, memo section updates, and monitoring deltas — v1.0
- ✓ End-to-end vertical slice plus full panel surface with weekly refresh and delta generation — v1.0
- ✓ CLI and FastAPI interfaces for ingestion, coverage, analysis, memo, deltas, queue, review, and notifications — v1.0
- ✓ Sample data, generated artifacts, and comprehensive test suite — v1.0
- ✓ Real LLM providers (OpenAI, Anthropic, Google Gemini, Groq, OpenAI-compatible) with env-driven toggling and provider chain fallback — v2.0
- ✓ API key authentication with role-based access control (operator/readonly) and configurable CORS — v2.0
- ✓ Production Docker (multi-stage build, health/ready probes, dev/prod profiles, credential safety) — v2.0
- ✓ Structured JSON logging with run context, per-invocation token tracking, and retry resilience — v2.0
- ✓ Token usage tracking, cost estimation, and configurable per-run budget cap — v2.0
- ✓ GitHub Actions CI pipeline (lint, type check, tests) with no external dependencies — v2.0
- ✓ Complete operator documentation: production setup guide, test/prod toggling, vendor dashboard links — v2.0

### Active

(None — next milestone requirements to be defined)

### Out of Scope

- Frontend application — the system remains API/CLI only.
- Premium live data vendor integrations (Bloomberg, FactSet) — stub connectors stay; free-tier connectors may be explored separately.
- Compliance, entitlement, and restricted-information workflows — still excluded.
- Kubernetes or cloud-managed container orchestration — the system targets reliable single-host Docker deployment.
- OAuth-based LLM authentication — all supported providers use API keys for programmatic access.

## Context

The system ships 11,600+ LOC of Python source code and 8,500+ LOC of tests. The tech stack is Python 3.11+, LangGraph, FastAPI, SQLAlchemy, Postgres, Docker, and structlog. The runtime supports 6 LLM provider backends (fake, OpenAI, Anthropic, Google Gemini, Groq, OpenAI-compatible) with chain-based fallback and per-run token budgets.

Both public and private company workflows are supported. Public workflows ingest filings, transcripts, price/volume, ownership, and event-style evidence; private workflows ingest dataroom, KPI, contract, cap table, and diligence-style evidence. The memo is a living artifact that stays readable even while only some panels have completed.

The project-wide gatekeeper policy: every run enters `gatekeepers` first; `pass` and `review` continue automatically; `fail` stops for review with operator-only provisional continuation.

## Constraints

- **Architecture**: Config-driven cohort topology — agent graph behavior derived from registries, not embedded in business logic.
- **Runtime**: LangGraph-centered orchestration — reusable subgraphs for debate, gatekeeping, memo updates, monitoring, and synthesis.
- **Persistence**: Postgres-first storage — structured records survive weekly reruns with status-transition history.
- **Interface**: API/CLI only — no frontend in current scope.
- **Testing**: Fake-provider testable — core flows never require live API calls.
- **Deployment**: Docker-first — dev and prod profiles with credential enforcement.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Use Python 3.11+ with `uv` | LangGraph requires Python >= 3.10, `uv` simplifies env setup | ✓ Good |
| Use YAML registries for cohort configuration | Agents, panels, factors, tool bundles, memo sections, run policies must be editable without code changes | ✓ Good |
| Use SQLAlchemy + Postgres JSON/JSONB persistence | Typed records plus flexible payloads and history retention | ✓ Good |
| Implement one full production vertical slice first | Architecture matters more than breadth; gatekeepers + demand prove memo updates and rerun deltas | ✓ Good |
| Keep public and private ingestion separate behind shared spine | Evidence sources differ materially even with shared downstream contracts | ✓ Good |
| Auto-continue passed/review gatekeepers, queue and notify failures | Operators review only failures; provisional analysis stays explicit | ✓ Good |
| Provider chain with automatic fallback | Resilience: if primary provider fails, system tries next without operator intervention | ✓ Good (v2.0) |
| API key auth with role-based middleware | Simple, stateless auth appropriate for API-first deployment; no OAuth complexity | ✓ Good (v2.0) |
| Multi-stage Dockerfile with separate dev/prod profiles | Keeps dev agile while prod excludes test data and dev deps | ✓ Good (v2.0) |
| Token budget enforcement at graph execution level | Graceful mid-run abort prevents unbounded LLM spending | ✓ Good (v2.0) |

## Completed Milestones

- **v1.0** — Phases 1–8: Core platform, all panels productionized, full vertical slice, config-driven orchestration, memory persistence, CLI/API, queue operations
- **v2.0** — Phases 9–13: Real LLM providers, API security, deployment hardening, cost controls, CI/CD, operator documentation

---
*Last updated: 2026-03-16 after v2.0 milestone completion*
