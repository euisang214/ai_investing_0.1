# Runbook

## Docker-First Workflow

1. Start Postgres with Docker Compose.
2. Initialize the database.
3. Ingest sample evidence.
4. Add a coverage entry.
5. Inspect cadence policies and assign a schedule.
6. Run an analysis or enqueue scheduled work.
7. Inspect the queue, review queue, notifications, memo, and delta outputs.

## Recommended Commands

```bash
docker compose up --build -d
docker compose exec api ai-investing init-db
docker compose exec api ai-investing ingest-public-data /app/examples/acme_public
docker compose exec api ai-investing add-coverage ACME "Acme Cloud" public watchlist
docker compose exec api ai-investing list-cadence-policies
docker compose exec api ai-investing set-coverage-schedule ACME --schedule-policy-id weekday_morning
docker compose exec api ai-investing analyze-company ACME
docker compose exec api ai-investing enqueue-watchlist
docker compose exec api ai-investing run-worker --worker-id local --max-concurrency 2
```

## Checkpoint Workflow

Every company analysis still enters `gatekeepers` first. The difference in Phase 5 is that the checkpoint is now auto-resolved for `pass` and `review`, while `fail` remains a blocking review state.

1. Start the run with `ai-investing analyze-company ACME`, `ai-investing refresh-company ACME`, or
   `POST /companies/{company_id}/analyze`.
2. Read the returned `run.run_id`.
3. Use `ai-investing show-run <run_id>` or `GET /runs/{run_id}` to retrieve the persisted run.
4. Look at the structured fields instead of parsing prose:
   `gate_decision`, `awaiting_continue`, `gated_out`, `stopped_after_panel`, `provisional`,
   `checkpoint_panel_id`, and `checkpoint.allowed_actions`.
5. If `gate_decision` is `pass` or `review`, the run should already be terminal. The checkpoint record stays on the run for auditability, but `awaiting_continue` is `false` and `checkpoint.resolution_action` should already be `continue`.
6. If `gate_decision` is `fail`, downstream work is blocked until the operator reviews the queue entry and explicitly chooses
   `ai-investing continue-run <run_id> --provisional` or
   `{"action": "continue_provisional"}`.
7. `--stop` remains valid when an operator wants to finalize a failed gatekeeper run without any provisional downstream work.

## What Exists Before And After Continue

- The gatekeeper verdict, memo projection, and checkpoint metadata are persisted for every run, even when the checkpoint is auto-resolved.
- Successful pass or review runs can already emit final memo and delta artifacts because downstream work completes automatically.
- Failed gatekeeper runs stay at `awaiting_continue` and do not emit a terminal monitoring delta until the operator stops or resumes provisionally.
- Stopping after `gatekeepers` keeps the full memo shape visible; sections without downstream work remain `not_advanced` or `stale` instead of disappearing.
- Provisional resumes keep `provisional: true` on the run payload so downstream output stays visibly exploratory.

## Cadence Policies

Use cadence policies for recurring operations instead of hardcoding weekly behavior in automation.

```bash
docker compose exec api ai-investing list-cadence-policies
docker compose exec api ai-investing set-coverage-schedule ACME --schedule-policy-id weekday_morning
docker compose exec api ai-investing set-coverage-schedule ACME --schedule-disabled
docker compose exec api ai-investing set-next-run-at ACME 2026-03-17T09:30:00+00:00
```

- `schedule_policy_id` is the primary cadence control for scheduled refreshes.
- `schedule_enabled` lets operators disable recurring runs without deleting coverage.
- `preferred_run_time` keeps timing explicit while preserving one shared workspace timezone.
- `set-next-run-at` remains useful for one-off overrides and manual testing.

## Queue Submission And Worker Execution

Scheduled and bulk operations should enqueue jobs instead of running all reasoning inline.

```bash
docker compose exec api ai-investing queue-summary
docker compose exec api ai-investing enqueue-companies ACME BETA
docker compose exec api ai-investing enqueue-watchlist
docker compose exec api ai-investing enqueue-portfolio
docker compose exec api ai-investing enqueue-due-coverage
docker compose exec api ai-investing show-job <job_id>
docker compose exec api ai-investing retry-job <job_id>
docker compose exec api ai-investing cancel-job <job_id> --reason "coverage disabled"
docker compose exec api ai-investing force-run-job <job_id>
docker compose exec api ai-investing run-worker --worker-id local --max-concurrency 2
```

- `enqueue-companies` is for a hand-picked set of company ids.
- `enqueue-watchlist` and `enqueue-portfolio` are the bulk operator entrypoints.
- `enqueue-due-coverage` is the scheduling-friendly surface for cron or n8n.
- `run-worker` executes bounded parallel queue work inside the service runtime.
- `queue-summary` and `show-job` expose queue state without requiring direct database access.

## Review Queue And Provisional Overrides

- `ai-investing run-due-coverage` and `POST /coverage/run-due` preserve the same checkpoint flow.
  They remain available for local debugging, but scheduled automation should prefer queue submission.
- If a company is already paused at `awaiting_continue`, the existing paused run is returned instead
  of silently starting a new one.
- `ai-investing run-panel` and `POST /companies/{company_id}/panels/{panel_id}/run` can only start
  with `gatekeepers`.
- Direct downstream panel execution such as `demand_revenue_quality` requires an existing paused run
  plus an explicit continue action.
- Failed gatekeepers appear in `ai-investing list-review-queue` and `GET /review-queue`.
- Review-queue items are first-class operational records linked to the run, job, and notification event.
- No worker, webhook, or n8n flow may call `continue-run --provisional` automatically.

## Notifications

Notifications are created by the service and delivered by external automation against stable endpoints.

```bash
docker compose exec api ai-investing list-notifications
docker compose exec api ai-investing claim-notifications --consumer-id n8n
docker compose exec api ai-investing dispatch-notification <event_id>
docker compose exec api ai-investing acknowledge-notification <event_id>
```

- immediate alerts fire for failed gatekeepers, worker failures, and materially changed successful runs
- the daily digest includes successful runs with no key changes so operators can confirm coverage still processed
- notification records include the company, summary, next action, and any linked job or review ids
- external tooling should claim and dispatch notifications; it should not infer them from memo text or database reads

## Operator Examples

```bash
docker compose exec api ai-investing analyze-company ACME
docker compose exec api ai-investing show-run <run_id>
docker compose exec api ai-investing continue-run <run_id> --stop
docker compose exec api ai-investing continue-run <run_id> --provisional
docker compose exec api ai-investing run-panel ACME gatekeepers
docker compose exec api ai-investing queue-summary
docker compose exec api ai-investing enqueue-watchlist
docker compose exec api ai-investing list-review-queue
docker compose exec api ai-investing list-notifications
docker compose exec api ai-investing generate-memo ACME
docker compose exec api ai-investing show-delta ACME
```

## HTTP API Surfaces

Use these endpoints when wiring external automation:

- `POST /queue/enqueue-selected`
- `POST /queue/enqueue-watchlist`
- `POST /queue/enqueue-portfolio`
- `POST /queue/enqueue-due`
- `GET /queue`
- `GET /queue/{job_id}`
- `GET /review-queue`
- `POST /workers/run`
- `GET /notifications`
- `POST /notifications/claim`
- `POST /notifications/{event_id}/dispatch`
- `POST /notifications/{event_id}/acknowledge`

Keep n8n and other schedulers on those API and webhook boundaries. They should not coordinate worker-internal callbacks, panel sequencing, or provisional continuation logic.

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
