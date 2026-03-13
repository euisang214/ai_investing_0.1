# AI Investing

AI Investing is a config-driven multi-agent investment research platform for public and private company analysis. It preserves structured factor-level memory, consolidates panel verdicts, maintains a living IC memo, and produces rerun deltas for covered names.

## What Is Implemented Today

The productionized vertical slice is intentionally narrow:

- YAML-driven cohort, factor, tool, memo-section, connector, and run-policy registries
- typed schemas and Postgres-backed persistence
- file-based public/private ingestion
- working panel execution for `gatekeepers`
- working panel execution for `demand_revenue_quality`
- section-level memo updates during the run
- rerun delta generation
- FastAPI and Typer interfaces
- sample data, n8n workflow examples, and automated tests

## Current Panel Status

Implemented and runnable today:

- `gatekeepers`
- `demand_revenue_quality`

Scaffold-only and visible in config, but not runnable yet:

- `supply_product_operations`
- `market_structure_growth`
- `macro_industry_transmission`
- `management_governance_capital_allocation`
- `financial_quality_liquidity_economic_model`
- `external_regulatory_geopolitical`
- `expectations_catalyst_realization`
- `security_or_deal_overlay`
- `portfolio_fit_positioning`

This distinction matters operationally. `config/panels.yaml` and `config/run_policies.yaml` intentionally keep the full planned panel topology inspectable, including future-facing policies such as `full_surface`. That future-facing surface is allowed to exist in config before it is runnable. The runtime still blocks execution when a selected policy or explicit panel list includes scaffold-only panels, so visibility in config does not mean production readiness.

## Short Extension Checklist

Use this high-level checklist before treating any scaffold-only panel as runnable:

1. Confirm the panel contract in `config/panels.yaml`, including `implemented`, `memo_section_ids`, and `factor_ids`.
2. Expand the panel agent tree in `config/agents.yaml` instead of hardcoding topology in orchestration.
3. Keep factor ownership and descriptions aligned in `config/factors.yaml`.
4. Replace scaffold prompts in `prompts/` with implementation-ready panel and agent prompts.
5. Add or update tests in `tests/` that prove the new panel works and that scaffold boundaries remain explicit.
6. Change runtime code only if the abstraction truly needs expansion; config and prompt work should remain the default path.

Need the full file-by-file path? See the [panel extension guide](docs/panel_extension_path.md).

## Quick Start

Docker is the primary local workflow. The host workflow is supported only when Python 3.11+ is available.

```bash
docker compose up --build -d
docker compose exec api ai-investing init-db
docker compose exec api ai-investing ingest-public-data /app/examples/acme_public
docker compose exec api ai-investing add-coverage ACME "Acme Cloud" public watchlist
docker compose exec api ai-investing set-next-run-at ACME 2026-03-10T09:30:00+00:00
docker compose exec api ai-investing analyze-company ACME
# inspect the returned run_id while the run is paused after gatekeepers
docker compose exec api ai-investing show-run <run_id>
# continue after a passed or review gatekeeper
docker compose exec api ai-investing continue-run <run_id>
# or finalize at the checkpoint without downstream analysis
docker compose exec api ai-investing continue-run <run_id> --stop
docker compose exec api ai-investing generate-memo ACME
```

`analyze-company`, `refresh-company`, and `run-due-coverage` do not silently continue past the mandatory `gatekeepers` checkpoint. Their JSON payloads expose structured lifecycle fields such as `gate_decision`, `awaiting_continue`, `gated_out`, `stopped_after_panel`, and `provisional`. Use `continue-run <run_id> --provisional` only when a failed gatekeeper needs exploratory downstream analysis.

## Host Workflow

Only use this path when `python --version` reports Python 3.11 or newer.

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
ai-investing init-db
```

## Example CLI Commands

```bash
ai-investing init-db
ai-investing ingest-public-data examples/acme_public
ai-investing ingest-private-data examples/beta_private
ai-investing add-coverage ACME "Acme Cloud" public watchlist
ai-investing list-coverage
ai-investing disable-coverage ACME
ai-investing set-next-run-at ACME 2026-03-10T09:30:00+00:00
ai-investing remove-coverage ACME
ai-investing analyze-company ACME
ai-investing show-run run_123
ai-investing continue-run run_123
ai-investing continue-run run_123 --stop
ai-investing continue-run run_123 --provisional
ai-investing run-panel ACME gatekeepers
ai-investing refresh-company ACME
ai-investing run-due-coverage
ai-investing generate-memo ACME
ai-investing show-delta ACME
ai-investing list-agents
ai-investing enable-agent demand_skeptic
ai-investing disable-agent demand_skeptic
ai-investing reparent-agent demand_skeptic demand_advocate
```

## Monitoring Read Surfaces

Phase 4 adds additive operator-facing inspection surfaces for monitoring history and portfolio
monitoring. They are read-only projections over persisted coverage, run, and monitoring records.
They do not create a frontend, they do not widen orchestration, and they do not make
`portfolio_fit_positioning` runnable.

Operator CLI examples:

```bash
ai-investing show-monitoring-history ACME --limit 5
ai-investing show-portfolio-summary
ai-investing show-portfolio-summary --segment portfolio
```

Matching API routes:

- `GET /companies/{company_id}/monitoring-history`
- `GET /portfolio/monitoring-summary`

The portfolio monitoring summary includes both portfolio and watchlist names by default, but it
keeps those segments separate in every response. Operators should read the summary by change type
first, then by segment. Shared-risk or overlap clusters appear ahead of exploratory analog
drill-down so the main portfolio monitoring view stays actionable instead of becoming a blended
company list.

## Repo Layout

See [docs/architecture.md](docs/architecture.md), [docs/factor_ontology.md](docs/factor_ontology.md), [docs/memory_model.md](docs/memory_model.md), and [docs/runbook.md](docs/runbook.md).

For the explicit scaffold-to-production handoff, start with the [panel extension guide](docs/panel_extension_path.md).

The operator workflow for paused gatekeeper runs, explicit continue actions, provisional overrides, and run inspection lives in [docs/runbook.md](docs/runbook.md).

## Next Backlog

- productionize the remaining panels
- deepen contradiction and analog services
- add more realistic public/private connector adapters
- add worker infrastructure for larger scheduled coverage sets
