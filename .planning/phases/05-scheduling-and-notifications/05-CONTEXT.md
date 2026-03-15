# Phase 5: Scheduling And Notifications - Context

**Gathered:** 2026-03-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 5 moves the project from local repeatability to reliable recurring operations. The phase covers configurable cadence policies beyond weekly defaults, a background execution and review-queue model for recurring refreshes, and clear n8n and notification boundaries. The scope stays inside the existing backend-first architecture: n8n remains external, scheduling stays config-driven, and provisional overrides remain operator-controlled rather than automated.

</domain>

<decisions>
## Implementation Decisions

### Cadence control
- Phase 5 should add built-in cadence presets plus one small advanced option rather than forcing every company onto a freeform schedule.
- Operators should be able to disable scheduled runs entirely for a coverage entry.
- Per-company scheduling should allow a cadence policy plus a preferred run time.
- The system should use one workspace timezone for all schedules rather than per-company timezones.
- If the system misses multiple scheduled windows while down, it should run once when it comes back and then roll forward from the next future slot rather than replaying every missed occurrence.

### Manual run selection
- Operators should be able to run refreshes manually for selected companies.
- Operators should also be able to trigger manual refreshes for the whole watchlist or the whole portfolio.
- Manual runs should use the same gatekeeper policy as scheduled runs rather than preserving a separate universal-pause path.

### Gatekeeper automation policy
- Every run still enters `gatekeepers` first.
- If `gatekeepers` returns `pass` or `review`, the run should continue automatically into downstream work for both scheduled and initial runs.
- If `gatekeepers` returns `fail`, the run should stop after `gatekeepers`, enter a review queue, and notify immediately.
- Failed gatekeepers should remain reviewable and queryable instead of being treated as generic worker failures.
- Downstream work after a failed gatekeeper remains exploratory/provisional rather than equivalent to a normal passed run.

### Provisional override policy
- Provisional downstream analysis may never be automatic.
- A failed gatekeeper can continue downstream only after an explicit operator action.
- n8n and background workers must not trigger provisional continuation on their own.

### Notification behavior
- Immediate notifications should fire for failed gatekeepers, worker or runtime failures, and materially changed successful runs.
- Notifications should go to one shared operator channel for now.
- Immediate notifications should include the company, a short change summary, and the required next action.
- Successful non-failed runs should also roll into a daily digest.
- The daily digest should include a per-company summary of key changes, and explicitly say when a company had no key changes.

### Background operator controls
- Operators should be able to inspect a queue summary plus per-job status.
- Operators should be able to retry, cancel, and force-run queued jobs.
- Bulk manual runs for the watchlist or portfolio should enqueue work instead of executing everything inline.
- Background execution should run multiple companies in parallel rather than waiting for each company to finish before the next starts.
- The most important operator-facing background summary is what failed and needs action.

### Claude's Discretion
- Choose the exact built-in cadence presets and the one small advanced scheduling option as long as the default operator surface stays simple and disabling schedules remains explicit.
- Choose the exact review-queue data model and notification-event schema as long as failed gatekeepers are first-class, queryable records.
- Choose the exact manual-run surface for selected companies, watchlist, and portfolio scopes as long as it stays additive to the existing CLI and API.
- Choose the exact notification channel abstraction as long as the first implementation can distinguish failed-gatekeeper review alerts from normal successful completion events.

</decisions>

<specifics>
## Specific Ideas

- The old project rule that every run pauses after `gatekeepers` is no longer valid.
- The new project-wide rule applies to both initial and scheduled runs: `pass` and `review` continue automatically, while `fail` stops into review plus immediate notification.
- Scheduling should support explicit disablement, not just `manual` as an implicit workaround.
- Manual operation should be able to target one company, a hand-picked set of companies, the full watchlist, or the full portfolio.
- One shared operator notification channel is enough for Phase 5 even if routing becomes more granular later.
- Daily digests should still mention companies with no key changes so operators can tell they were processed successfully.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/ai_investing/domain/models.py`: `CoverageEntry` already stores `cadence`, `next_run_at`, and `last_run_at`, and `RunRecord` already stores `gate_decision`, `gated_out`, `provisional`, and checkpoint metadata.
- `src/ai_investing/application/services.py`: `CoverageService` and `AnalysisService.run_due_coverage()` already own coverage scheduling and run triggering, making them the natural seams for Phase 5 scheduling and worker changes.
- `src/ai_investing/persistence/repositories.py`: due-coverage selection already exists and can be extended into queue or review-oriented repository helpers.
- `src/ai_investing/cli.py` and `src/ai_investing/api/main.py`: current interfaces already expose coverage creation, `set-next-run-at`, due-run triggering, run inspection, and explicit continuation commands.
- `config/tool_registry.yaml`: a stub `send_notification` tool already exists and can anchor a more honest notification boundary.
- `n8n/README.md` plus the existing JSON examples already establish that n8n should call the service rather than host the reasoning runtime.

### Established Patterns
- The repo prefers config-driven operator behavior rather than hardcoded branching spread across CLI, API, and orchestration.
- n8n is an external scheduling and notification boundary, not the reasoning runtime.
- Structured records and additive operator surfaces are preferred over prose-only or hidden state.
- The current code still pauses all runs after `gatekeepers`, but that behavior is now a temporary mismatch rather than a locked product rule.

### Integration Points
- Cadence-policy work will center on coverage models, scheduling services, repository queries, and additive CLI or API controls.
- Review-queue and notification work will center on run lifecycle persistence, worker-facing services, and a typed notification or outbox seam.
- Manual multi-company triggers will likely extend the current coverage and analysis service surface instead of creating a separate orchestration path.
- Queue inspection and job-level controls will likely extend the current CLI and API surface rather than requiring a separate operational interface.
- n8n example updates will center on `n8n/*.json`, `README.md`, and `docs/runbook.md`.

</code_context>

<deferred>
## Deferred Ideas

- Per-company timezones are out of scope for Phase 5.
- Automatic provisional analysis after a failed gatekeeper is out of scope for Phase 5.
- Replaying every missed scheduled occurrence as a separate catch-up run is out of scope for Phase 5.
- Splitting notifications into different destination channels by coverage segment is deferred beyond the first Phase 5 cut.

</deferred>

---

*Phase: 05-scheduling-and-notifications*
*Context gathered: 2026-03-13*
