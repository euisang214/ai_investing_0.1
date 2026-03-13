---
phase: 04-monitoring-and-connectors
plan: 03
subsystem: monitoring
tags: [monitoring, delta, analogs, contradictions, config]
requires:
  - phase: 04-01
    provides: registry-backed connector runtime and persisted rerun baselines used by monitoring refreshes
provides:
  - config-backed monitoring delta computation
  - deterministic analog and base-rate ranking over structured evidence
  - shared contradiction and analog services for runtime and builtin tools
  - richer additive MonitoringDelta detail fields and updated generated examples
affects: [memo-delta, builtin-tools, generated-examples, docs]
tech-stack:
  added: []
  patterns: [config-driven monitoring rules, shared monitoring services, additive delta serialization]
key-files:
  created:
    [
      src/ai_investing/monitoring/__init__.py,
      src/ai_investing/monitoring/analog_graph.py,
      src/ai_investing/monitoring/service.py,
      tests/test_analog_graph.py,
    ]
  modified:
    [
      src/ai_investing/application/services.py,
      src/ai_investing/domain/models.py,
      src/ai_investing/tools/builtins.py,
      config/monitoring.yaml,
      prompts/monitoring/delta.md,
      docs/monitoring.md,
      tests/test_monitoring_semantics.py,
    ]
key-decisions:
  - "Delegate refresh-time monitoring through MonitoringDeltaService and keep RefreshRuntime focused on memo projection and persistence."
  - "Drive drift, contradiction, analog, and concentration behavior from config so monitoring semantics stay editable without runtime rewrites."
  - "Require evidence-backed contradictions before surfacing factor conflicts so skeptical-agent phrasing does not create false positives."
patterns-established:
  - "Monitoring services can enrich output additively while preserving old persisted payloads and generated examples."
  - "Builtin monitoring tools should call the same service layer the refresh runtime uses."
requirements-completed: [V2-04A]
duration: 12min
completed: 2026-03-13
---

# Phase 4 Plan 3: Richer Monitoring Services Summary

**Config-backed monitoring deltas with deterministic analog ranking, factor-level contradiction support, and additive current-state dependency details**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-13T01:10:10Z
- **Completed:** 2026-03-13T01:21:50Z
- **Tasks:** 3
- **Files modified:** 19

## Accomplishments

- Moved monitoring delta computation behind a dedicated service seam and expanded `config/monitoring.yaml` into live drift, contradiction, analog, and concentration rules.
- Added additive `MonitoringDelta` detail fields plus deterministic analog/base-rate ranking and shared contradiction analysis for both runtime and builtin tools.
- Updated the monitoring prompt, operator docs, and checked-in generated examples so the richer delta contract is documented and reproducible.

## Task Commits

Each task was committed atomically:

1. **Task 1: Extract a reusable monitoring service and make rule mapping config-driven** - `ed6468c` (`feat`)
2. **Task 2: Add analog or base-rate references, contradiction support, and additive delta fields** - `af63131` (`feat`)
3. **Task 3: Refresh monitoring prompt and docs, then lock compatibility with regressions** - `11c5880` (`docs`)

**Follow-up fix:** `6e4ca0e` (`fix`) tightened contradiction detection and cleared lint after the generated-example regression exposed skeptic-only noise.

## Files Created/Modified

- `src/ai_investing/monitoring/service.py` - shared monitoring delta service, contradiction handling, and concentration views
- `src/ai_investing/monitoring/analog_graph.py` - deterministic analog and base-rate ranking over structured factor signals
- `src/ai_investing/domain/models.py` - additive `MonitoringDelta` detail records with backward-compatible serialization
- `src/ai_investing/tools/builtins.py` - shared contradiction and analog tool delegation
- `config/monitoring.yaml` - live monitoring rules for drift, contradiction, analog, and concentration behavior
- `tests/test_monitoring_semantics.py` - regressions for contradictions, current-state concentration, and backward compatibility
- `tests/test_analog_graph.py` - deterministic analog ranking and builtin delegation coverage
- `docs/monitoring.md` - operator-facing monitoring contract and compatibility notes

## Decisions Made

- Kept `RefreshRuntime` responsible for memo-section updates and persistence only; monitoring enrichment now lives in reusable services.
- Preserved the original `MonitoringDelta` top-level contract and added richer fields only as optional detail structures.
- Treated analogs and contradictions as shared monitoring capabilities rather than separate tool-only heuristics.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Pulled typed monitoring support forward to unblock the new service seam**
- **Found during:** Task 1
- **Issue:** The new monitoring service and config-backed rule mapping could not compile cleanly against the old minimal monitoring config and delta model.
- **Fix:** Added typed monitoring config sections and additive `MonitoringDelta` detail models during the service extraction step instead of waiting for the later task boundary.
- **Files modified:** `src/ai_investing/config/models.py`, `src/ai_investing/domain/models.py`
- **Verification:** `docker compose run --rm api pytest -q tests/test_monitoring_semantics.py tests/test_run_lifecycle.py -k "monitoring or drift or concentration"`
- **Committed in:** `ed6468c`

**2. [Rule 1 - Bug] Tightened contradiction detection after generated examples surfaced skeptic-only noise**
- **Found during:** Task 3
- **Issue:** Contradictions were being raised when the skeptic claim disagreed with otherwise one-sided evidence, which polluted the generated example artifacts.
- **Fix:** Required evidence-backed contradictory stances before surfacing factor conflicts and then reran lint and regression verification.
- **Files modified:** `src/ai_investing/monitoring/service.py`, `tests/test_monitoring_semantics.py`, `tests/test_analog_graph.py`
- **Verification:** `docker compose run --rm api pytest -q tests/test_monitoring_semantics.py tests/test_run_lifecycle.py`, `docker compose run --rm api pytest -q tests/test_analog_graph.py`, `docker compose run --rm api ruff check src tests`
- **Committed in:** `6e4ca0e`

**3. [Rule 3 - Blocking] Regenerated checked-in examples after the richer delta payload changed deterministic artifacts**
- **Found during:** Task 3
- **Issue:** `tests/test_generated_examples.py` failed because the richer monitoring output changed the generated ACME rerun artifacts.
- **Fix:** Regenerated the checked-in examples from the updated runtime so the repo fixtures describe the shipped monitoring surface.
- **Files modified:** `examples/generated/ACME/continued/delta.json`, `examples/generated/ACME/continued/result.json`, `examples/generated/ACME/rerun/delta.json`, `examples/generated/ACME/rerun/memo.md`, `examples/generated/ACME/rerun/result.json`
- **Verification:** `docker compose run --rm api pytest -q tests/test_generated_examples.py`
- **Committed in:** `11c5880`

---

**Total deviations:** 3 auto-fixed (1 bug, 2 blocking)
**Impact on plan:** The deviations kept the monitoring service coherent, preserved deterministic artifacts, and avoided scope creep outside the Phase 4 monitoring contract.

## Issues Encountered

- The first full verification pass was blocked by Ruff import-order and line-length errors in the new monitoring files; these were fixed before the final verification run.
- Generated example artifacts drifted after the richer delta payload shipped, which required regeneration to keep the checked-in fixtures deterministic.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Monitoring now exposes reusable contradiction, analog/base-rate, and current-state dependency signals that `04-04` can consume for history and portfolio-level read models.
- The richer delta contract is documented and regression-locked, so later monitoring surfaces can build on these details without reopening memo compatibility work.

## Self-Check: PASSED

- Verified summary and key implementation files exist on disk.
- Verified task and follow-up fix commits `ed6468c`, `af63131`, `11c5880`, and `6e4ca0e` resolve as commit objects.
