# Runbook

## Docker-First Workflow

```bash
docker compose up --build -d
docker compose exec api ai-investing init-db
docker compose exec api ai-investing ingest-public-data /app/examples/acme_public
docker compose exec api ai-investing add-coverage ACME "Acme Cloud" public watchlist
docker compose exec api ai-investing analyze-company ACME
docker compose exec api ai-investing show-run <run_id>
docker compose exec api ai-investing generate-memo ACME
docker compose exec api ai-investing show-delta ACME
```

Use the host workflow only when Python 3.11+ is available locally.

## Choosing A Run Policy

Coverage policy determines how wide the panel surface is for a run.

- `weekly_default`: use for the narrow recurring operator baseline
- `internal_company_quality`: use when you want the full internal company-quality family
- `external_company_quality`: use when you also want market and regulatory context
- `expectations_rollout`: use when you want the company-quality surface plus `expectations_catalyst_realization`
- `full_surface`: use when you also want `security_or_deal_overlay` and `portfolio_fit_positioning`

The wider policies do not force unsupported panels to fabricate output. They still honor the support contract per run.

## Checkpoint Workflow

Every run enters `gatekeepers` first.

1. Start the run with `ai-investing analyze-company ACME`, `ai-investing refresh-company ACME`, or the matching API route.
2. Capture the returned `run_id`.
3. Inspect the persisted run with `ai-investing show-run <run_id>` or `GET /runs/{run_id}`.
4. Read structured state instead of memo prose alone:
   `gate_decision`, `awaiting_continue`, `checkpoint_panel_id`, `checkpoint`, `panel_support_assessments`, and `skipped_panels`.

Checkpoint behavior is:

- `pass`: auto-continue
- `review`: auto-continue
- `fail`: stop for review and require explicit operator-only provisional continuation or stop

## Reading Panel Support

Each selected panel surfaces one of three support states:

- `supported`
- `weak_confidence`
- `unsupported`

Interpret them as follows:

### Supported

The configured readiness bar was satisfied. Read the panel verdict and affected memo sections normally.

### Weak Confidence

The panel still ran, but the evidence or factor coverage is thinner than the preferred readiness bar. The run payload records that status explicitly, and affected memo sections call out weak confidence so the operator does not need to inspect raw evidence counts manually.

This is most relevant for company-quality families such as:

- `supply_product_operations`
- `market_structure_growth`
- `management_governance_capital_allocation`
- `financial_quality_liquidity_economic_model`

### Unsupported

The panel did not run. The runtime records:

- a `support` object with `status: unsupported`
- a `skip` object with a reason code and missing context or evidence detail

The run continues. Unsupported panels do not abort the full analysis unless the operator intentionally stops the run earlier.

## Reading Partial Recommendations

`overall_recommendation` is intentionally scoped.

- If a narrower policy such as `expectations_rollout` ran, the memo should say that the security or deal overlay is pending for that rollout and that portfolio fit positioning has not been added yet.
- If `full_surface` ran but overlay context was unavailable, the memo should say the relevant overlay was unsupported for this run.
- If both overlays ran successfully, the recommendation scope is complete across company quality, expectations, `security_or_deal_overlay`, and `portfolio_fit_positioning`.

A partial recommendation is still useful. Read it as the best available conclusion for the executed surface, not as a silent claim that every panel family completed.

## Overlay Support Rules

Overlay handling is stricter than ordinary company-quality panels.

- `security_or_deal_overlay` requires overlay-specific context and evidence
- `portfolio_fit_positioning` requires portfolio context

Neither overlay falls back to weak confidence today. Missing overlay support yields an explicit skip.

This is the expected behavior for runs where:

- the operator chooses `full_surface` without loading overlay evidence
- the company has company-quality support but no book-aware portfolio context

## Queue And Review Operations

Use queue-backed commands for scheduled or batch work.

```bash
docker compose exec api ai-investing queue-summary
docker compose exec api ai-investing enqueue-watchlist
docker compose exec api ai-investing enqueue-portfolio
docker compose exec api ai-investing enqueue-due-coverage
docker compose exec api ai-investing run-worker --worker-id local --max-concurrency 2
docker compose exec api ai-investing list-review-queue
docker compose exec api ai-investing list-notifications
```

Key rules:

- queue jobs execute the same analysis runtime as direct operator runs
- failed gatekeepers create review-queue items
- no worker or external automation flow may call provisional continuation automatically

## Generated Artifact Inspection

Checked artifacts under `examples/generated/ACME/` provide a stable operator reference for the shipped Phase 6 contract.

- `initial/`: initial run output
- `continued/`: persisted reread of that same completed run
- `rerun/`: rerun with delta output against the prior active memo
- `overlay_gap/`: `full_surface` output where company-quality and expectations panels complete, but overlays are skipped explicitly because support context is missing

Inspect in this order:

1. `result.json` for run metadata, support states, and skipped panels
2. `memo.md` for how sections and `overall_recommendation` render
3. `delta.json` for rerun changes

## Common Operator Reads

### Company-quality only

If you are using `weekly_default`, `internal_company_quality`, or `external_company_quality`, treat the memo as intentionally incomplete on overlays. That is policy choice, not runtime failure.

### Expectations included, overlays not selected

If `expectations_rollout` ran, `expectations_catalyst_realization` should be present, and `overall_recommendation` should still describe overlay work as pending rather than complete.

### Full surface with unsupported overlays

If `full_surface` ran and overlays show `unsupported`, the correct conclusion is:

- company-quality work still completed
- overlay support was absent for this run
- the memo should not imply that skipped overlays disappeared

### Full surface with supported overlays

If `security_or_deal_overlay` and `portfolio_fit_positioning` both show `supported`, the run has the full panel surface and the recommendation scope can be read as overlay-complete.

## HTTP API Surfaces

Use these endpoints for automation:

- `POST /companies/{company_id}/analyze`
- `POST /companies/{company_id}/refresh`
- `GET /runs/{run_id}`
- `GET /review-queue`
- `POST /queue/enqueue-watchlist`
- `POST /queue/enqueue-portfolio`
- `POST /queue/enqueue-due`
- `POST /workers/run`
- `GET /notifications`
- `POST /notifications/claim`
- `POST /notifications/{event_id}/dispatch`
- `POST /notifications/{event_id}/acknowledge`

Keep external automation on those boundaries. It should not coordinate panel sequencing or infer recommendation scope by scraping memo text.

## Regenerating Checked Examples

```bash
docker compose run --rm api python scripts/generate_phase2_examples.py
docker compose run --rm api pytest -q tests/test_generated_examples.py
```

Those commands keep the docs, checked artifacts, and regression contract synchronized.
