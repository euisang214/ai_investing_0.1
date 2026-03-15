# AI Investing

## What This Is

AI Investing is a modular multi-agent investment research platform for public and private company analysis. It ingests structured evidence, runs a config-driven cohort of specialist and panel agents, preserves factor-level memory over time, and maintains a living investment committee memo that updates section-by-section as analysis completes.

The initial release is backend-only. It targets research teams that need repeatable weekly refreshes for watchlist and portfolio companies without hardcoding panel topology into orchestration logic.

## Core Value

Produce a continuously updatable, auditable investment view where factor-level claims, panel verdicts, and memo deltas remain structured and reusable across reruns.

## Requirements

### Validated

- [x] Config-driven multi-agent orchestration with all 11 top-level panels productionized.
- [x] Typed persistence for evidence, claims, verdicts, memo snapshots, memo section updates, and monitoring deltas.
- [x] End-to-end vertical slice plus full panel surface with weekly refresh and delta generation.
- [x] CLI and FastAPI interfaces for ingestion, coverage, analysis, memo, deltas, queue, review, and notifications.
- [x] Sample data, generated artifacts, and comprehensive test suite.

### Active

- [ ] Switch from fake providers to real LLM providers (OpenAI, Anthropic) with proper secrets management and test/prod toggling.
- [ ] Add API authentication, CORS, HTTPS readiness, and role-based access control.
- [ ] Harden deployment: production Docker image, health checks, CI/CD pipeline, environment separation.
- [ ] Add structured logging, metrics, error tracking, and LLM call tracing.
- [ ] Add token usage tracking, cost estimation, rate limit handling, and per-run budget controls.
- [ ] Document all manual operator steps (API key creation, secrets setup) in README with clear instructions.

### Out of Scope

- Frontend application — v2 remains API/CLI only.
- Premium live data vendor integrations (Bloomberg, FactSet) — stub connectors stay in place; free-tier connectors may be explored separately.
- Compliance, entitlement, and restricted-information workflows — still excluded.
- Kubernetes or cloud-managed container orchestration — v2 targets reliable single-host Docker deployment with CI/CD readiness.

## Context

The target system must support both public and private company workflows. Public workflows need filings, transcripts, price/volume, ownership, and event-style evidence; private workflows need dataroom, KPI, contract, cap table, and diligence-style evidence. The memo is a living artifact and must stay readable even while only some panels have completed.

The architecture must keep graph orchestration, provider abstraction, persistence, prompts, schemas, ingestion, tool registry, and interfaces separated. Agents, panels, factors, prompts, tool bundles, schemas, and memo sections should be editable through configuration wherever practical. n8n is an external scheduling and notification boundary, not the reasoning runtime.

The project-wide gatekeeper policy is now: every run enters `gatekeepers` first; `pass` and `review` continue automatically into downstream work; `fail` stops after `gatekeepers`, enters a review queue, and notifies immediately; provisional downstream analysis remains an explicit operator-only override.

## Constraints

- **Architecture**: Config-driven cohort topology — agent graph behavior must be derived from registries rather than embedded in business logic.
- **Runtime**: LangGraph-centered orchestration — reusable subgraphs should handle debate, gatekeeping, memo updates, monitoring, and final synthesis.
- **Persistence**: Postgres-first storage — structured records must survive weekly reruns and preserve history with status transitions.
- **Interface**: No frontend in v1 — CLI and FastAPI must cover all workflows.
- **Testing**: Model-dependent logic must be testable with fake providers — core flows cannot require live API calls to validate.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Use Python 3.11+ with `uv` | Current LangGraph releases require Python >= 3.10, and `uv` keeps local/devcontainer setup simple | — Pending |
| Use YAML registries for cohort configuration | Agents, panels, factors, tool bundles, memo sections, and run policies need to be editable without runtime rewrites | — Pending |
| Use SQLAlchemy + Postgres JSON/JSONB persistence | The system needs typed records plus flexible payloads and history retention across heterogeneous memory objects | — Pending |
| Implement only one full production vertical slice first | The architecture matters more than breadth; gatekeepers + demand prove memo updates and rerun deltas end-to-end | — Pending |
| Keep public and private ingestion modules separate behind a shared spine | The evidence sources differ materially even when downstream memory contracts are shared | — Pending |
| Auto-continue passed or review gatekeepers, queue and notify failed gatekeepers | The universal pause rule is no longer desired; operators should review only failures by default while keeping provisional analysis explicit | — Pending |

## Current Milestone: v2.0 Productionization

**Goal:** Take the dev-only research runtime to a production-deployable state with real LLM providers, security, observability, cost controls, and documented operator workflows.

**Target features:**
- Real LLM provider integration with env-driven test/prod toggle
- API authentication and authorization (API keys or JWT)
- Production Docker hardening (multi-stage build, health checks, no dev deps)
- Structured logging, metrics, and error tracking
- Token usage tracking, cost estimation, and rate limit resilience
- CI/CD pipeline configuration
- Operator documentation for all manual setup steps

---
*Last updated: 2026-03-15 after v2.0 milestone start*
