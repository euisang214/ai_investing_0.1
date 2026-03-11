---
phase: 02-vertical-slice-and-delta-flow
plan: 04
subsystem: testing
tags: [pytest, docker, fixtures, examples, delta]
requires:
  - phase: 02-02
    provides: checkpoint lifecycle fields, memo posture semantics, and materiality-aware deltas
  - phase: 02-03
    provides: tool-log provenance and stale-evidence semantics for the vertical slice
provides:
  - Deterministic Phase 2 example generation through a repo-local script
  - End-to-end regression coverage for pause, continue, provisional continue, rerun, and due-skip flows
  - Inspectable ACME artifacts for paused, continued, and rerun states
affects: [phase-03, phase-04, docs, operator-workflows]
tech-stack:
  added: []
  patterns: [deterministic fixture clocks, checked-in artifact parity tests, Docker-first verification]
key-files:
  created:
    [
      scripts/generate_phase2_examples.py,
      tests/test_generated_examples.py,
      examples/generated/README.md,
      examples/generated/ACME/continued/result.json,
      examples/generated/ACME/continued/memo.md,
      examples/generated/ACME/continued/delta.json,
      examples/generated/ACME/initial/delta.json
    ]
  modified:
    [
      Dockerfile,
      docker-compose.yml,
      src/ai_investing/domain/models.py,
      src/ai_investing/ingestion/file_connectors.py,
      tests/conftest.py,
      tests/test_analysis_flow.py,
      examples/generated/ACME/initial/result.json,
      examples/generated/ACME/initial/memo.md,
      examples/generated/ACME/rerun/result.json,
      examples/generated/ACME/rerun/memo.md,
      examples/generated/ACME/rerun/delta.json
    ]
key-decisions:
  - "Generate ACME artifacts through the same AnalysisService entrypoints the app exposes, not a parallel sample runtime."
  - "Enforce reproducibility by driving IDs and timestamps through patchable shared clock/id seams, then lock checked-in files to generator output."
  - "Verify the plan in Docker because the host machine still defaults to Python 3.9 while the repo targets Python 3.11+."
patterns-established:
  - "Deterministic Runtime Harness: tests and scripts patch shared ID/time helpers to keep lifecycle outputs reproducible."
  - "Artifact Parity Testing: checked-in JSON and memo files must match a fresh generator run byte-for-byte."
requirements-completed: [TEST-01, TEST-02, TOOLS-02]
duration: 10min
completed: 2026-03-11
---

# Phase 2 Plan 04: Vertical Slice Regression And Artifact Summary

**Deterministic fake-provider checkpoint artifacts and end-to-end regressions for paused, continued, and rerun Phase 2 flows**

## Performance

- **Duration:** 10 min
- **Started:** 2026-03-11T03:35:35Z
- **Completed:** 2026-03-11T03:45:27Z
- **Tasks:** 3
- **Files modified:** 18

## Accomplishments

- Added a repo-local `scripts/generate_phase2_examples.py` flow that reproduces paused, continued, and rerun ACME artifacts through the real application services.
- Rewrote the Phase 2 regression surface around the actual checkpoint contract, including explicit continue, provisional continue, rerun delta behavior, disabled due coverage, and persisted tool-log refs.
- Checked in refreshed ACME artifacts plus a README, and locked them to the generator with parity tests.

## Task Commits

Each task was committed atomically:

1. **Task 1: Stabilize fixtures and sample generation for checkpointed runs** - `3c28a30` (feat)
2. **Task 2: Expand end-to-end regression coverage for the full Phase 2 workflow** - `084a2a5` (test)
3. **Task 3: Refresh the checked-in Phase 2 sample artifacts** - `501bf15` (feat)

**Verification follow-up:** `b1c4dbc` (test) - lint-cleaned the deterministic fixture for host and Docker compatibility.

## Files Created/Modified

- `scripts/generate_phase2_examples.py` - Reproducible ACME artifact generation over the real services
- `tests/conftest.py` - Deterministic clock/id fixture harness shared across Phase 2 tests
- `tests/test_analysis_flow.py` - End-to-end lifecycle and tool-log regression coverage
- `tests/test_generated_examples.py` - Generator and artifact parity assertions
- `src/ai_investing/domain/models.py` - Lambda-wrapped timestamp defaults so patched clocks affect model creation
- `src/ai_investing/ingestion/file_connectors.py` - Shared clock usage for deterministic staleness calculation
- `Dockerfile` - Copies repo scripts into the primary verification image
- `docker-compose.yml` - Mounts the `scripts/` directory into the `api` service
- `examples/generated/README.md` - Artifact guide and regeneration instructions
- `examples/generated/ACME/initial/result.json` - Paused-after-gatekeepers example output
- `examples/generated/ACME/continued/result.json` - Explicitly continued full-run output
- `examples/generated/ACME/rerun/delta.json` - Materiality-aware rerun delta artifact

## Decisions Made

- Used the existing `AnalysisService` and fake-provider stack for artifact generation so the examples prove the public workflow instead of a bespoke example-only path.
- Fixed timestamp defaults in domain models rather than normalizing generated JSON afterward, because reproducibility needed to hold at the object-creation layer.
- Kept verification Docker-first to match the repo’s documented primary workflow and avoid false negatives from the host Python 3.9 runtime.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Routed ingestion staleness through the shared clock**
- **Found during:** Task 1 (Stabilize fixtures and sample generation for checkpointed runs)
- **Issue:** `FileBundleConnector._staleness_days()` used `datetime.now()` directly, so regenerated examples drifted even when the rest of the runtime was patched to deterministic time.
- **Fix:** Switched staleness calculation to the shared `utc_now()` helper.
- **Files modified:** `src/ai_investing/ingestion/file_connectors.py`
- **Verification:** `docker compose run --rm api pytest -q tests/test_generated_examples.py -k generation`
- **Committed in:** `3c28a30`

**2. [Rule 3 - Blocking] Exposed the generator script inside the Docker workflow**
- **Found during:** Task 1 (Stabilize fixtures and sample generation for checkpointed runs)
- **Issue:** The repo’s primary `docker compose` workflow could not see `scripts/generate_phase2_examples.py`, so supported-runtime verification failed with `FileNotFoundError`.
- **Fix:** Copied and mounted `scripts/` into the `api` image and container.
- **Files modified:** `Dockerfile`, `docker-compose.yml`
- **Verification:** `docker compose run --rm api pytest -q tests/test_generated_examples.py -k generation`
- **Committed in:** `3c28a30`

**3. [Rule 1 - Bug] Made model timestamps patchable for deterministic generation**
- **Found during:** Task 3 (Refresh the checked-in Phase 2 sample artifacts)
- **Issue:** Timestamp fields captured the original `utc_now` function at import time, so fresh generator runs still emitted nondeterministic timestamps and failed artifact parity checks.
- **Fix:** Changed timestamp field defaults to lambda wrappers that call `utc_now()` at instantiation time.
- **Files modified:** `src/ai_investing/domain/models.py`
- **Verification:** `docker compose run --rm api pytest -q tests/test_generated_examples.py`
- **Committed in:** `501bf15`

**4. [Rule 3 - Blocking] Kept the deterministic fixture compatible with both lint and the host runtime**
- **Found during:** Verification
- **Issue:** The deterministic test clock needed a Python 3.9-safe UTC fallback, but the first compatibility fix violated the repo’s Ruff rules.
- **Fix:** Added a lint-safe UTC fallback constant and wrapped the fixture signature.
- **Files modified:** `tests/conftest.py`
- **Verification:** `docker compose run --rm api sh -lc 'pytest -q tests/test_run_lifecycle.py tests/test_monitoring_semantics.py tests/test_analysis_flow.py tests/test_cli.py tests/test_api.py tests/test_generated_examples.py tests/test_config_and_registry.py tests/test_ingestion.py && ruff check src tests && python scripts/generate_phase2_examples.py'`
- **Committed in:** `b1c4dbc`

---

**Total deviations:** 4 auto-fixed (2 bug, 2 blocking)
**Impact on plan:** All four fixes were required to make the generator reproducible and to verify it through the repo’s supported Docker path. No architectural scope change was introduced.

## Issues Encountered

- The host machine only exposed Python 3.9, so direct host-side pytest runs could not exercise the repository’s 3.11-only LangGraph stack. Verification was moved to the documented Docker workflow.
- Dynamic loading of the generator script inside tests initially failed because the temporary import module was not registered in `sys.modules`. The artifact test helper now registers the module before execution.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 2 now has reproducible artifacts and regression coverage for the full pause/continue/rerun story.
- Future phases can extend panel coverage without re-deriving how checkpointed runs should look on disk or in tests.
- No execution blockers remain for moving into Phase 3 planning/execution.

## Self-Check: PASSED

- Found `.planning/phases/02-vertical-slice-and-delta-flow/02-04-SUMMARY.md`
- Found commit `3c28a30`
- Found commit `084a2a5`
- Found commit `501bf15`
- Found commit `b1c4dbc`
