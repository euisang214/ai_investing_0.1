# Architecture

## Overview

This repository implements a modular multi-agent investment research platform for public and private company analysis. The design treats factor-level memory, panel verdicts, and memo section updates as first-class structured records, then composes company refreshes from reusable LangGraph subgraphs instead of bespoke workflows.

The initial production scope is deliberately narrow:

- full vertical slice for `gatekeepers`
- full vertical slice for `demand_revenue_quality`
- living memo updates during the run
- rerun delta generation against the prior active memo

The rest of the panel surface area is scaffolded in configuration and prompts so it can be expanded without rewriting orchestration core code.

## Current Panel Topology

The current runtime intentionally separates implemented panels from scaffold-only panels.

Implemented and runnable today:

- `gatekeepers`
- `demand_revenue_quality`

Scaffold-only panels that already exist in registry and prompt assets:

- `supply_product_operations`
- `market_structure_growth`
- `macro_industry_transmission`
- `management_governance_capital_allocation`
- `financial_quality_liquidity_economic_model`
- `external_regulatory_geopolitical`
- `expectations_catalyst_realization`
- `security_or_deal_overlay`
- `portfolio_fit_positioning`

This topology is config-driven on purpose. The repository needs the eventual panel map to be editable in YAML long before every panel has a safe execution path. That is why future-facing policies can appear in config before those panels are runnable.

## Runtime Boundary For Scaffold-Only Panels

Three rules define the current posture:

1. `config/panels.yaml` is the source of truth for the intended panel inventory, even when some entries are scaffold-only.
2. `config/run_policies.yaml` may expose future-facing policies such as `full_surface` so operators and engineers can inspect the planned topology.
3. Execution still rejects scaffold-only panels until the required agents, prompts, tests, and verification coverage exist.

The important operational point is that "present in config" is not the same as "approved for production runs." Config visibility helps maintainability and extension planning. Runtime safety still depends on the execution guardrails that block unimplemented panels before partial work starts.

## Target Runtime

- Python `3.11+`
- `uv` for environment and dependency management
- FastAPI for the service layer
- Typer for the CLI
- LangGraph for orchestration
- SQLAlchemy + Postgres for persistence
- Pydantic v2 for schemas
- Docker Compose for local Postgres-backed development

## Assumptions

- v1 users are engineers or research operators comfortable with CLI/API workflows.
- Evidence ingestion can begin with local files and sample adapters rather than live vendor APIs.
- Weekly reruns are the default cadence, but cadence is a policy concern and must remain configurable.
- The first useful outcome is a strong backend contract and one trustworthy vertical slice, not full coverage of every panel.
- Postgres is the source of truth for persisted state; vector search is optional and loosely coupled.

## Explicit Non-Goals

- Frontend application or analyst UI
- Compliance, entitlement, or restricted-information workflow controls
- Production-ready live integrations for premium public or private data vendors
- Full implementation of every panel's reasoning logic in v1
- Autonomous portfolio execution or trade routing

## Proposed File Tree

```text
.
|-- .planning/
|-- config/
|   |-- agents.yaml
|   |-- factors.yaml
|   |-- memo_sections.yaml
|   |-- model_profiles.yaml
|   |-- monitoring.yaml
|   |-- panels.yaml
|   |-- run_policies.yaml
|   |-- source_connectors.yaml
|   |-- tool_bundles.yaml
|   `-- tool_registry.yaml
|-- docs/
|   |-- architecture.md
|   |-- factor_ontology.md
|   |-- ingestion.md
|   |-- memory_model.md
|   |-- monitoring.md
|   |-- prompting_strategy.md
|   |-- runbook.md
|   `-- tool_registry.md
|-- examples/
|   |-- acme_public/
|   |-- acme_public_rerun/
|   |-- beta_private/
|   `-- generated/
|-- n8n/
|-- prompts/
|   |-- gatekeepers/
|   |-- ic/
|   |-- memo_updates/
|   |-- monitoring/
|   `-- panels/
|-- src/
|   `-- ai_investing/
|       |-- api/
|       |-- application/
|       |-- config/
|       |-- domain/
|       |-- graphs/
|       |-- ingestion/
|       |-- persistence/
|       |-- prompts/
|       |-- providers/
|       |-- tools/
|       `-- cli.py
|-- tests/
|-- docker-compose.yml
|-- Dockerfile
|-- pyproject.toml
`-- README.md
```

## System Layers

### 1. Configuration Layer

YAML registries define panels, factors, agents, memo sections, tool bundles, model profiles, run policies, and source connectors. Runtime services consume validated config objects, so adding a factor or agent requires config and prompt updates instead of orchestration rewrites.

For scaffold-only panels, the key files are:

- `config/panels.yaml` for panel-level contracts, factor coverage, and memo-section mapping
- `config/agents.yaml` for disabled placeholder or later production agent trees
- `config/factors.yaml` for factor ownership and descriptions
- `prompts/` for panel and agent instructions that stay editable outside the runtime

### 2. Domain Contract Layer

Pydantic models describe the canonical record types:

- `CoverageEntry`
- `CompanyProfile`
- `EvidenceRecord`
- `ClaimCard`
- `PanelVerdict`
- `GatekeeperVerdict`
- `MemoSection`
- `MemoSectionUpdate`
- `ICMemo`
- `MonitoringDelta`
- `ToolInvocationLog`
- `RunRecord`

These models are the handoff contracts between ingestion, orchestration, memo logic, and interfaces.

### 3. Persistence Layer

Postgres stores typed records in explicit tables with JSON payloads where necessary. Historical records are never destructively overwritten; instead, active records can be superseded or rejected. This keeps memo history, claim history, and run-to-run drift analyzable.

### 4. Orchestration Layer

LangGraph composes reusable subgraphs:

- `GatekeeperSubgraph`
- `DebateSubgraph`
- `PanelLeadSubgraph`
- `MemoUpdateSubgraph`
- `MonitoringDiffSubgraph`
- `ICSynthesisGraph`
- `CompanyRefreshGraph`

The `CompanyRefreshGraph` loads due panels from config and run policy, executes the active subgraphs, persists outputs, and updates memo sections incrementally.

The first production checkpoint is mandatory:

- `gatekeepers` always runs before downstream panels
- the graph pauses after `gatekeepers` even when the company passes
- downstream work resumes only after an explicit operator action
- failed gatekeepers can continue only as provisional analysis
- direct downstream `run-panel` execution is rejected unless the run already has the required resume context

That same orchestration layer also enforces the Phase 3 scaffold boundary:

- config may name scaffold-only panels
- policies may reference scaffold-only panels
- execution may inspect scaffold-only topology
- runtime may not treat scaffold-only panels as runnable until implementation work is complete

### 5. Provider Layer

`ModelProvider` adapters shield the domain logic from provider-specific SDKs. v1 includes:

- `FakeModelProvider` for deterministic tests and sample artifacts
- `OpenAIModelProvider`
- `AnthropicModelProvider`

Only the fake provider is required for tests and local sample runs.

### 6. Tool Layer

All tools are declared in `config/tool_registry.yaml` and attached to agents via `config/tool_bundles.yaml`. Tool execution is centralized so bundle enforcement and invocation logging happen in one place.

### 7. Interface Layer

Typer CLI and FastAPI endpoints both call the same application services. n8n stays outside the service boundary and interacts through HTTP and webhook-friendly APIs.

The operator-facing contract is checkpoint-aware:

- `analyze-company`, `refresh-company`, and due-coverage entrypoints return a structured run payload
- `show-run` and `GET /runs/{run_id}` expose persisted paused or completed runs by `run_id`
- `continue-run` and `POST /runs/{run_id}/continue` require an explicit action instead of silently chaining past the gatekeeper
- stable fields such as `gate_decision`, `awaiting_continue`, `gated_out`, `stopped_after_panel`, `provisional`, and `checkpoint` make automation clients parse state without scraping prose
- paused runs persist gatekeeper verdicts and partial memo artifacts immediately; terminal runs add final memo reconciliation and monitoring delta output

## Data Model And Memory Strategy

Each company uses stable namespace conventions:

- `company/{company_id}/profile`
- `company/{company_id}/evidence`
- `company/{company_id}/claims/{factor_id}`
- `company/{company_id}/debates/{panel_id}`
- `company/{company_id}/verdicts/{panel_id}`
- `company/{company_id}/memos/current`
- `company/{company_id}/memos/history`
- `company/{company_id}/monitoring`
- `company/{company_id}/tool_logs`
- `portfolio/framework_notes`
- `portfolio/analogs`

Structured tables, not a generic prose-only store, hold the real data. Namespace strings are stored alongside records so tools and agents can query coherently.

## Vertical Slice Scope

Phase 1 and Phase 2 implementation in this repo cover:

- config and prompt registries
- typed schemas and repositories
- public/private file-based ingestion
- coverage management
- reusable graph scaffolding
- working gatekeeper and demand panel flows
- section-level memo updates
- IC synthesis
- rerun delta generation
- API and CLI
- tests and sample outputs

Phase 3 adds the documentation, config breadth, and prompt scaffolding for the remaining panels, but it does not change the statement above: only `gatekeepers` and `demand_revenue_quality` are implemented today.

## Short Extension Checklist

Use this checklist before expanding a scaffold-only panel:

1. Start with `config/panels.yaml` and keep the panel id, memo sections, and factor mappings stable.
2. Add or expand the agent tree in `config/agents.yaml` rather than branching the graph for one panel.
3. Update factor contracts in `config/factors.yaml` so ontology and prompts do not drift.
4. Replace placeholder prompt assets in `prompts/` with implementation-ready instructions for the new agents.
5. Add verification in `tests/` for config loading, runtime behavior, and user-facing entrypoints.
6. Only change orchestration abstractions when the abstraction truly needs expansion; config-first extension is the default architecture rule.

## Tradeoffs

- SQLAlchemy is used instead of a lighter ad-hoc persistence layer because history-heavy typed records need explicit schemas and indexing.
- LangGraph is used even for a small initial slice because reusable subgraph composition is a core requirement, not a future enhancement.
- Only two panels are implemented deeply so the contracts stay credible before the system expands.
- `uv` is the chosen package manager even though some local hosts may not have it installed yet; the repo documents Docker-based fallback setup.
