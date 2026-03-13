---
phase: 04-monitoring-and-connectors
plan: 01
subsystem: ingestion
tags: [connectors, ingestion, pydantic, yaml, pytest]
requires:
  - phase: 02-vertical-slice-and-delta-flow
    provides: file-based ingestion, normalized evidence persistence, and stable public/private entrypoints
  - phase: 03-remaining-panel-scaffolds
    provides: registry validation patterns and config-driven runtime boundaries
provides:
  - connector config schema with backward-compatible settings, live-refresh posture, and evidence-policy fields
  - registry-backed connector resolution with default public/private fallbacks and explicit connector selection
  - regression coverage for connector validation, alias resolution, and unknown connector failures
affects: [04-02, ingestion-runtime, connector-docs]
tech-stack:
  added: []
  patterns:
    - registry-backed connector dispatch
    - backward-compatible config normalization
    - load-time connector validation
key-files:
  created:
    - src/ai_investing/ingestion/registry.py
    - tests/test_connector_runtime.py
  modified:
    - src/ai_investing/config/models.py
    - src/ai_investing/config/loader.py
    - src/ai_investing/ingestion/base.py
    - src/ai_investing/application/services.py
    - tests/test_config_and_registry.py
key-decisions:
  - Keep legacy manifest_file and raw_landing_zone fields valid while normalizing them into connector settings for future adapter growth.
  - Resolve connector ids through a dedicated registry and optional wrapper parameters instead of branching directly inside IngestionService.
  - Allow config-visible connector kinds like mcp_stub to validate at load time while failing clearly at runtime until a concrete builder is registered.
patterns-established:
  - "Connector config normalization: merge legacy top-level fields into typed settings and validate required settings per kind."
  - "Service-level compatibility wrappers: preserve ingest_public_data()/ingest_private_data() while routing runtime selection through connector_id."
requirements-completed: [V2-02A]
duration: 10min
completed: 2026-03-13
---

# Phase 4 Plan 01: Connector Runtime Seam Summary

**Registry-backed connector dispatch with backward-compatible file-bundle config, explicit connector selection, and load-time validation for malformed connector definitions**

## Performance

- **Duration:** 10 min
- **Started:** 2026-03-13T00:40:55Z
- **Completed:** 2026-03-13T00:51:10Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments

- Expanded `SourceConnectorConfig` so existing YAML still works while new connector definitions can declare additive `settings`, `live_refresh`, `evidence_policy`, and `capabilities`.
- Added a reusable ingestion registry that resolves connector ids to concrete runtime builders instead of instantiating `FileBundleConnector` inside `IngestionService`.
- Preserved the existing public/private ingestion entrypoints while allowing explicit `connector_id` selection and locking the seam with targeted config and runtime regressions.

## Task Commits

Each task was committed atomically:

1. **Task 1: Expand connector config and validation without breaking the current YAML** - `df9cddb` (`feat`)
2. **Task 2: Add a connector registry and route ingestion through it** - `88a150f` (`feat`)
3. **Task 3: Lock backward compatibility and failure behavior with targeted regressions** - `ae3a160` (`test`)
4. **Deviation fix: Resolve lint regressions surfaced by plan-wide verification** - `35e46fa` (`fix`)

## Files Created/Modified

- `src/ai_investing/config/models.py` - Adds backward-compatible connector settings, live-refresh, evidence-policy, and capability fields.
- `src/ai_investing/config/loader.py` - Validates supported connector kinds and required per-kind settings during registry load.
- `src/ai_investing/ingestion/base.py` - Defines typed connector ingest requests and resolved connector bindings.
- `src/ai_investing/ingestion/registry.py` - Maps configured connector ids to runtime builders and clear resolution errors.
- `src/ai_investing/application/services.py` - Routes ingestion through the registry while keeping existing public/private convenience wrappers.
- `tests/test_config_and_registry.py` - Covers connector schema normalization plus invalid kind and invalid settings failures.
- `tests/test_connector_runtime.py` - Covers default fallback, explicit alias selection, registry resolution, and unknown connector ids.

## Decisions Made

- Kept the current file-bundle YAML shape valid by normalizing legacy top-level fields into the new `settings` object instead of forcing an immediate config migration.
- Added runtime indirection in `src/ai_investing/ingestion/registry.py` rather than widening graph orchestration or moving connector-specific logic deeper into the system.
- Kept `mcp_stub` config-valid but not runnable until a concrete builder exists, so future connector additions stay explicit without pretending the stub works today.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed lint regressions introduced by the new connector seam**
- **Found during:** Final verification
- **Issue:** Newly added registry/runtime code introduced one import-style violation and two line-length violations, which blocked the required `ruff` pass.
- **Fix:** Switched `Callable` to `collections.abc`, wrapped the new connector ingest signature, and reformatted the runtime assertion in the regression suite.
- **Files modified:** `src/ai_investing/ingestion/base.py`, `src/ai_investing/ingestion/registry.py`, `tests/test_connector_runtime.py`
- **Verification:** `docker compose run --rm api pytest -q` and `docker compose run --rm api ruff check src tests`
- **Committed in:** `35e46fa`

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** The fix was required for the repo-wide verification gate and did not change scope or behavior.

## Issues Encountered

- One new config regression initially asserted the wrong failure path because it mixed mismatched legacy and explicit `raw_landing_zone` values; the test fixture was aligned to the intended missing-setting case before Task 1 verification passed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase `04-02` can add representative public and private adapters against a registry-backed ingestion seam instead of editing `IngestionService` branches again.
- Malformed connector definitions now fail during config load, so future adapter work has an explicit validation contract before runtime.

## Self-Check

PASSED

- Found `.planning/phases/04-monitoring-and-connectors/04-01-SUMMARY.md`
- Verified task and deviation commits: `df9cddb`, `88a150f`, `ae3a160`, `35e46fa`
