# AI Investing

AI Investing is a config-driven multi-agent investment research platform for public and private company analysis. It preserves structured factor-level memory, consolidates panel verdicts, maintains a living IC memo, and produces rerun deltas for covered names.

## What Is Implemented

- YAML-driven cohort, factor, tool, memo-section, connector, and run-policy registries
- typed schemas and Postgres-backed persistence
- file-based public/private ingestion
- working vertical slice for `gatekeepers` and `demand_revenue_quality`
- section-level memo updates during the run
- rerun delta generation
- FastAPI and Typer interfaces
- sample data, n8n workflow examples, and automated tests

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

`analyze-company`, `refresh-company`, and `run-due-coverage` do not silently continue past the
mandatory `gatekeepers` checkpoint. Their JSON payloads expose structured lifecycle fields such as
`gate_decision`, `awaiting_continue`, `gated_out`, `stopped_after_panel`, and `provisional`. Use
`continue-run <run_id> --provisional` only when a failed gatekeeper needs exploratory downstream
analysis.

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

## Repo Layout

See [docs/architecture.md](docs/architecture.md), [docs/memory_model.md](docs/memory_model.md), and [docs/runbook.md](docs/runbook.md).

The operator workflow for paused gatekeeper runs, explicit continue actions, provisional overrides,
and run inspection lives in [docs/runbook.md](docs/runbook.md).

## Next Backlog

- productionize the remaining panels
- deepen contradiction and analog services
- add more realistic public/private connector adapters
- add worker infrastructure for larger scheduled coverage sets
