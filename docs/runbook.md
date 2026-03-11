# Runbook

## Docker-First Workflow

1. Start Postgres with Docker Compose.
2. Initialize the database.
3. Ingest sample evidence.
4. Add a coverage entry.
5. Optionally set the next scheduled refresh.
6. Run an analysis or refresh.
7. Inspect the memo and delta outputs.

## Recommended Commands

```bash
docker compose up --build -d
docker compose exec api ai-investing init-db
docker compose exec api ai-investing ingest-public-data /app/examples/acme_public
docker compose exec api ai-investing add-coverage ACME "Acme Cloud" public watchlist
docker compose exec api ai-investing set-next-run-at ACME 2026-03-10T09:30:00+00:00
docker compose exec api ai-investing analyze-company ACME
```

## Checkpoint Workflow

Every company analysis enters `gatekeepers` first and then pauses. The run is not considered
complete until an operator explicitly chooses what happens after that checkpoint.

1. Start the run with `ai-investing analyze-company ACME`, `ai-investing refresh-company ACME`, or
   `POST /companies/{company_id}/analyze`.
2. Read the returned `run.run_id` and inspect the paused payload.
3. Use `ai-investing show-run <run_id>` or `GET /runs/{run_id}` to retrieve the persisted run.
4. Look at the structured fields instead of parsing prose:
   `gate_decision`, `awaiting_continue`, `gated_out`, `stopped_after_panel`, `provisional`,
   `checkpoint_panel_id`, and `checkpoint.allowed_actions`.
5. Resume intentionally:
   `ai-investing continue-run <run_id>` or `POST /runs/{run_id}/continue` with
   `{"action": "continue"}`.
6. Finalize at the checkpoint without downstream work:
   `ai-investing continue-run <run_id> --stop` or `{"action": "stop"}`.
7. If `gate_decision` is `fail`, downstream work is blocked unless the operator chooses
   `ai-investing continue-run <run_id> --provisional` or
   `{"action": "continue_provisional"}`.

## What Exists Before And After Continue

- While a run is paused at `awaiting_continue`, the gatekeeper verdict and partial memo are already
  persisted and queryable by `run_id`.
- A paused run does not emit a final monitoring delta yet.
- When an operator resumes or stops the run, the system writes the terminal memo and delta artifacts.
- Stopping after `gatekeepers` keeps the full memo shape visible; sections without downstream work
  remain `not_advanced` or `stale` instead of disappearing.
- Provisional resumes keep `provisional: true` on the run payload so downstream output stays visibly
  exploratory.

## Due Coverage And Panel Rules

- `ai-investing run-due-coverage` and `POST /coverage/run-due` preserve the same checkpoint flow.
  If a company is already paused at `awaiting_continue`, the existing paused run is returned instead
  of silently starting a new one.
- `ai-investing run-panel` and `POST /companies/{company_id}/panels/{panel_id}/run` can only start
  with `gatekeepers`.
- Direct downstream panel execution such as `demand_revenue_quality` requires an existing paused run
  plus an explicit continue action.

## Operator Examples

```bash
docker compose exec api ai-investing analyze-company ACME
docker compose exec api ai-investing show-run <run_id>
docker compose exec api ai-investing continue-run <run_id>
docker compose exec api ai-investing continue-run <run_id> --stop
docker compose exec api ai-investing continue-run <run_id> --provisional
docker compose exec api ai-investing run-panel ACME gatekeepers
docker compose exec api ai-investing generate-memo ACME
docker compose exec api ai-investing show-delta ACME
```

## Host Workflow

Only use the host workflow when Python 3.11+ is available locally.

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
ai-investing init-db
```

## Python Version Note

The project target runtime is Python 3.11+ because current LangGraph releases require Python 3.10 or newer. Docker remains the recommended path when the host interpreter is older or missing the project dependencies.
