# Phase 2: Vertical Slice And Delta Flow - Context

**Gathered:** 2026-03-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 2 proves one end-to-end vertical slice for a single company: ingestion-backed gatekeeper review, optional continuation into `demand_revenue_quality`, section-by-section memo updates, final IC memo reconciliation, and rerun delta generation. Scope stays limited to `gatekeepers` and `demand_revenue_quality`, plus the operator-facing behavior needed to run, pause, continue, and inspect this slice through the existing CLI/API surface.

</domain>

<decisions>
## Implementation Decisions

### Gatekeeper checkpoint behavior
- `gatekeepers` is a mandatory checkpoint, not just the first panel in a fixed sequence.
- Every run pauses after gatekeepers, even on a pass, and must surface that result before deeper work continues.
- This checkpoint applies across entrypoints. Do not silently auto-continue after gatekeepers.
- If gatekeepers passes, report that clearly and offer the user an explicit continue action for the rest of the run.
- If gatekeepers fails, the default outcome is to stop after gatekeepers, but the user may explicitly override and continue anyway.
- Any downstream work after a failed gatekeeper is exploratory/provisional, not equivalent to a normal passed run.
- If no continuation happens after gatekeepers, persist the stopped state and memo artifacts instead of treating the run as an abandoned partial failure.
- CLI/API results must expose explicit structured checkpoint fields such as `gate_decision`, `awaiting_continue`, `gated_out`, `stopped_after_panel`, and whether downstream output is provisional.

### Partial memo posture
- Keep the full required memo structure visible even when only part of the slice has run.
- When a section has never been advanced in any run, show it as explicitly not advanced yet rather than generic pending filler.
- When a rerun does not refresh a section but prior text exists, carry that prior text forward and mark the section stale.
- When a run stops after a gatekeeper pass without continuation, the memo should explicitly say the company passed screening but deeper panel work has not yet run.
- When a run stops after gatekeepers, only gatekeeper-supported sections should be refreshed; all other sections remain visible but not advanced or stale as appropriate.
- Operators should be able to distinguish current-run refreshed sections from carried-forward stale sections and from never-advanced sections.

### Delta sensitivity and rerun semantics
- A claim-level change is material when claim meaning changes or when confidence moves by at least `0.05`.
- Confidence changes below `0.05` should not create delta noise on their own.
- `what_changed_since_last_run` should update on every rerun because it acts as a run log section.
- Alerting should stay balanced: `high` for recommendation-level or core risk/gatekeeper changes, `medium` for meaningful claim drift, `low` otherwise.
- Delta summaries should emphasize material thesis movement, not purely cosmetic wording churn.
- Monitoring logic should continue to emit structured drift flags, but those flags should align with the stricter materiality rules above.

### Stale evidence handling
- Stale evidence should not silently pass through unchanged.
- By default, the system should proceed when evidence is stale but automatically downgrade confidence or output strength for the affected analysis.
- This stale-evidence rule should behave the same in manual, scheduled, and rerun flows.
- Stale-evidence visibility should appear in claim cards, affected memo sections, and the run/delta summary.
- Stale evidence should contribute to alerting only when it affects a key section or the recommendation, not as an automatic medium alert for every stale factor.

### Claude's Discretion
- Choose the exact continuation mechanism for paused gatekeeper checkpoints, as long as it is explicit in both CLI and API and does not silently auto-continue.
- Choose whether checkpoint state is represented through new run statuses, run metadata, or both, as long as paused/awaiting-continue outcomes are first-class and queryable.
- Choose the exact section labels and operator-facing copy for never-advanced versus stale sections, as long as operators can reliably tell the difference.
- Choose the exact field-by-field materiality comparison beyond claim meaning and confidence threshold, as long as rerun deltas stay balanced rather than noisy.
- Choose the exact confidence downgrade heuristic for stale evidence, as long as stale inputs visibly weaken affected outputs.

</decisions>

<specifics>
## Specific Ideas

- "Gatekeeper passed, deeper panel work not yet run." should be the operator-facing framing when a passed company stops at the checkpoint.
- A stopped-after-gatekeeper memo should still respect the required memo contract rather than collapse into an ad hoc one-off report.
- Overriding a failed gatekeeper should preserve a visible provisional or exploratory label on downstream analysis.
- `what_changed_since_last_run` is closer to a run log than a pure thesis section, so it should refresh on each rerun.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/ai_investing/graphs/company_refresh.py`: already sequences panels, memo updates, monitoring, and IC synthesis, and is the right place to introduce checkpoint or continue flow without hardcoding new panel topology.
- `src/ai_investing/graphs/subgraphs.py`: already separates gatekeeper, debate, panel-lead, memo, delta, and IC subgraphs and can host a gatekeeper decision branch without bespoke orchestration.
- `src/ai_investing/application/services.py`: `RefreshRuntime.update_memo_for_panel`, `compute_monitoring_delta`, `_build_memo`, and `_run_company` already centralize partial memo, delta, and result assembly behavior.
- `src/ai_investing/domain/enums.py`: `MemoSectionStatus` already includes `stale`, but `RunStatus` has no paused or checkpoint state and `MemoSectionStatus` has no `not_advanced` value yet.
- `src/ai_investing/domain/models.py`: `GatekeeperVerdict`, `MemoSection`, `MonitoringDelta`, and `RunRecord` already provide the typed contract surface that Phase 2 should extend rather than bypass.
- `src/ai_investing/cli.py` and `src/ai_investing/api/main.py`: current entrypoints already expose analyze, refresh, panel, memo, and delta flows and should surface checkpoint-aware responses instead of inventing a parallel operator interface.
- `config/monitoring.yaml`: current alert thresholds are config-driven and can absorb the balanced materiality rules instead of embedding them in orchestration logic.
- `tests/test_analysis_flow.py`: existing vertical-slice tests already cover graph composition, memo semantics, reruns, and failure behavior and can be extended for checkpointed runs, stale sections, and refined delta rules.

### Established Patterns
- Phase 1 already locked config-driven orchestration and current-state-by-default reads; Phase 2 should keep behavioral choices explicit in typed records and configs rather than hidden in prompt text.
- Partial memo writes already happen after each panel verdict, so gatekeeper stop states should reuse that incremental memo pattern rather than introduce a second memo pipeline.
- History is preserved through superseding records, so paused or provisional runs should still persist structured artifacts instead of mutating prior active state in place.
- Tool logging, claim generation, and verdict persistence already run through shared services, which should remain the single place where continuation and provisional markers are attached.

### Integration Points
- Gatekeeper checkpoint flow will center on `src/ai_investing/graphs/company_refresh.py`, `src/ai_investing/graphs/subgraphs.py`, `src/ai_investing/application/services.py`, and the run/result schemas in `src/ai_investing/domain/models.py`.
- Partial memo status changes will center on `src/ai_investing/domain/enums.py`, `src/ai_investing/domain/models.py`, memo construction in `src/ai_investing/application/services.py`, and memo rendering helpers.
- Delta sensitivity changes will center on `src/ai_investing/application/services.py`, `config/monitoring.yaml`, and the fake-provider sample artifacts under `examples/generated/`.
- Operator checkpoint and continue behavior will require aligned CLI/API response contracts in `src/ai_investing/cli.py`, `src/ai_investing/api/main.py`, and corresponding tests.
- Sample artifact expectations will need to expand so deterministic examples cover gatekeeper-only stop states, continued runs, and rerun deltas under the new materiality rules.

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-vertical-slice-and-delta-flow*
*Context gathered: 2026-03-10*
