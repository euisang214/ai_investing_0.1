# Phase 5 Research: Scheduling And Notifications

## Scope Snapshot

- Phase 5 targets `V2-03` and `V2-05`.
- Goal: move from single-process local repeatability to reliable recurring operations without changing the reasoning runtime boundary.
- Success criteria narrow the phase: add configurable cadence policies beyond weekly, make the n8n examples cover refreshes plus webhooks and notifications honestly, and introduce background execution plus notification boundaries that stay separate from LangGraph reasoning.

## Current Repo State Relevant To Phase 5

- Coverage scheduling is real but narrow. `CoverageEntry` stores `cadence`, `next_run_at`, `last_run_at`, and `panel_policy`, and the repository can already select due coverage by `next_run_at`.
- The current cadence contract is hardcoded to `weekly` or `manual`. `CoverageService.add_coverage()` auto-schedules only weekly entries, and `AnalysisService._execute_run()` only advances `next_run_at` by seven days after a terminal weekly run.
- `run_due_coverage()` is synchronous and sequential inside the API or CLI process. It preserves the checkpoint contract correctly by returning existing paused runs instead of starting duplicate work, but it is not a background worker seam and it does not expose queue state.
- Current operator surfaces are useful but incomplete for recurring operations. CLI and API can add coverage, set `next_run_at`, run due coverage, inspect runs, and continue paused runs, but they cannot manage cadence policy definitions, queued refresh jobs, or notification delivery state.
- The repo already has an external automation boundary. `n8n/weekly_watchlist_refresh.json`, `n8n/weekly_portfolio_refresh.json`, `n8n/new_evidence_webhook.json`, and `n8n/refresh_notification.json` exist, but they are thin examples that mostly call `/coverage/run-due` or an ingest endpoint directly and do not describe the intended worker or notification contract.
- Notifications are only hinted at today. `config/tool_registry.yaml` contains a stub `send_notification` tool, but there is no typed notification event or outbox model and no explicit dispatch boundary.
- The current universal gatekeeper pause behavior is now a known mismatch with project direction. Phase 5 must reconcile the runtime with the new contract: `pass` and `review` auto-continue, while `fail` stops after `gatekeepers`, enters a review queue, and notifies immediately.

## Implementation Seams And Constraints

- Keep cadence config-driven. Phase 5 should not grow a long-lived chain of `if cadence == ...` branches through `AnalysisService`, CLI, and API code. Named cadence policies with typed config are a better fit than a widening enum-only contract.
- Preserve backward compatibility for existing weekly workflows. Current coverage entries, run policies, CLI commands, API payloads, and tests should keep working while Phase 5 adds richer schedule policy options.
- Treat background execution as a separate application seam. A worker should consume queued refresh work from structured records; FastAPI request handlers and n8n flows should enqueue or trigger work, not become the worker.
- Keep n8n outside the reasoning runtime. n8n may schedule API calls, receive webhook notifications, or orchestrate external side effects, but it should not own panel sequencing, memo updates, or provisional override logic.
- Preserve the new gatekeeper semantics under automation. A background worker should auto-continue `pass` and `review` results, but `fail` must stop into a reviewable queue state with immediate notification, and provisional analysis must remain explicit operator-only.
- Notifications should be event-driven and additive. They should derive from typed run, coverage, and delta records or a structured outbox record, not from parsing memo prose or duplicating reasoning logic in n8n.
- Keep verification Docker-first. The host Python version noted in `STATE.md` is still 3.9.6, so planning and implementation should continue to assume Docker-based verification for trustworthy results.

## Recommended Plan Breakdown

1. Cadence Policy Registry And Scheduling Semantics
   - Add a typed cadence-policy registry and a scheduling service that computes `next_run_at` from named policies instead of hardcoding weekly-only math.
   - Keep existing weekly coverage entries valid while adding richer policies such as weekday or interval schedules.
   - Update CLI, API, repository, and docs so operators can inspect and assign schedule policy choices without bypassing the current checkpointed refresh flow.

2. Background Refresh Queue And Notification Outbox
  - Add structured queued-work and notification-event records with repository helpers and a worker service that claims and processes jobs without moving logic into FastAPI or n8n.
  - Preserve run idempotency and the new gatekeeper policy so scheduled refreshes do not create duplicate active runs, automatically continue only `pass` and `review`, and surface failed gatekeepers as reviewable queued outcomes.
  - Make notifications flow from structured completion events or persisted deltas, not from ad hoc HTTP calls embedded in analysis code.

3. External Automation Examples And Operational Docs
   - Refresh the `n8n/` examples so they cover scheduled refresh submission, evidence webhook intake, and notification delivery against the new API or worker surfaces.
   - Document exactly where n8n stops and the service begins, including how workers, queues, paused runs, and notification dispatch interact.
   - Add operator runbook coverage for large scheduled refresh sets and the limits of the phase.

## Risks/Pitfalls

- Expanding the `Cadence` enum alone would make every future schedule change require runtime rewrites and will drift away from the repo's config-driven architecture rule.
- Reusing `/coverage/run-due` as both scheduler and worker API would keep the current synchronous bottleneck and blur the line between request handling and background execution.
- Automation can accidentally implement the new rule inconsistently across manual and scheduled entrypoints. Phase 5 needs one shared contract: `pass` and `review` continue, `fail` queues and notifies, provisional stays explicit.
- Notification delivery can become misleading if the phase sends generic success messages without capturing whether the run completed normally, stopped after a failed gatekeeper, or later resumed provisionally.
- n8n workflow examples can overclaim the architecture if they imply n8n is coordinating reasoning steps instead of calling stable API or webhook boundaries.
- Background concurrency can create duplicate refresh runs if the queue-claim model is not explicit and testable against the current repository patterns.

## Requirement Traceability

| Requirement | What Phase 5 should implement | Notes |
| --- | --- | --- |
| `V2-03` | Typed cadence-policy config, schedule computation, and operator-visible cadence selection beyond weekly defaults | Backward compatibility matters because weekly entries already exist in code, tests, docs, and examples. |
| `V2-05` | Structured background refresh queue plus notification outbox and worker-facing operational surfaces | This should be a service and persistence expansion, not a new orchestration runtime. |

## Validation Architecture

- Preserve existing run-lifecycle regressions where they still apply:
  - due coverage still skips disabled entries
  - `next_run_at` advances only on intended terminal outcomes
  - failed gatekeepers remain queryable and do not disappear into generic worker failure handling
  - provisional continuation remains explicit operator action only
- Add cadence-registry and scheduler tests:
  - config loading rejects invalid cadence policy definitions
  - weekly compatibility remains intact for existing coverage entries and defaults
  - new cadence-policy computation is deterministic for representative policies
  - manual cadence still stays unscheduled unless explicitly overridden
- Add queue and worker tests:
  - due coverage can be enqueued without immediately executing in the request path
  - worker claims do not create duplicate active runs for the same company
  - `pass` and `review` gatekeepers auto-continue for both initial and scheduled runs
  - `fail` gatekeepers stop into review-queue state and write immediate structured notification events rather than ad hoc side effects
- Add API and CLI tests:
  - cadence policy selection and due-work enqueue surfaces are additive and backward compatible
  - worker or queue inspection commands return structured state
  - existing `show-run` and explicit provisional follow-up flows remain usable even after pass or review auto-continue replaces the old universal pause rule
- Add docs and fixture validation:
  - `n8n/*.json` examples reference the intended API or webhook surfaces
  - docs explicitly state that n8n handles scheduling, webhook intake, and notifications, while the service owns reasoning, queue execution, and checkpoint state
- Keep the final verification Docker-based because that is the repo's supported Python 3.11 path.

## Planner Guidance

- Prefer a named cadence-policy registry over pushing raw cron strings directly into coverage entries. The repo needs a stable, validated scheduling contract that can evolve without touching every caller.
- Keep worker state and notification state as structured records so retries, failures, and operator inspection stay debuggable. Do not hide background execution inside web handlers.
- Treat queue submission, worker execution, and notification delivery as separate seams. That separation will make it easier to keep n8n external and optional.
- Make the n8n examples honest. They should demonstrate how to call the app, not suggest that the app is complete because an example JSON exists.
