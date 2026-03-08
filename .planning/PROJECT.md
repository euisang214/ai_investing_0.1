# AI Investing

## What This Is

AI Investing is a modular multi-agent investment research platform for public and private company analysis. It ingests structured evidence, runs a config-driven cohort of specialist and panel agents, preserves factor-level memory over time, and maintains a living investment committee memo that updates section-by-section as analysis completes.

The initial release is backend-only. It targets research teams that need repeatable weekly refreshes for watchlist and portfolio companies without hardcoding panel topology into orchestration logic.

## Core Value

Produce a continuously updatable, auditable investment view where factor-level claims, panel verdicts, and memo deltas remain structured and reusable across reruns.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Build a Python-first service with config-driven orchestration, typed schemas, and editable prompt files.
- [ ] Persist factor-level evidence, claims, verdicts, memo snapshots, memo section updates, and monitoring deltas without destructive overwrites.
- [ ] Deliver one end-to-end vertical slice for `gatekeepers` and `demand_revenue_quality`, including weekly refresh and delta generation.
- [ ] Expose both CLI and FastAPI interfaces for ingestion, coverage management, company analysis, memo retrieval, and agent toggles.
- [ ] Provide sample data, sample memo artifacts, tests, and local development tooling so another engineer can run the system without hidden context.

### Out of Scope

- Frontend application — v1 is API/CLI only so architecture and orchestration can stabilize first.
- Premium live data vendor integrations — phase 1 uses file-based and stub connectors to keep ingestion extensible without vendor lock-in.
- Compliance, entitlement, and restricted-information workflows — explicitly excluded from v1 to keep scope focused on research architecture.
- Fully implemented reasoning flows for every panel — only the initial vertical slice is productionized now; remaining panels are scaffolded for extension.

## Context

The target system must support both public and private company workflows. Public workflows need filings, transcripts, price/volume, ownership, and event-style evidence; private workflows need dataroom, KPI, contract, cap table, and diligence-style evidence. The memo is a living artifact and must stay readable even while only some panels have completed.

The architecture must keep graph orchestration, provider abstraction, persistence, prompts, schemas, ingestion, tool registry, and interfaces separated. Agents, panels, factors, prompts, tool bundles, schemas, and memo sections should be editable through configuration wherever practical. n8n is an external scheduling and notification boundary, not the reasoning runtime.

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

---
*Last updated: 2026-03-08 after initialization*
