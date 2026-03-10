---
phase: 01-foundation-and-contracts
plan: 02
subsystem: database
tags: [sqlalchemy, alembic, ingestion, memory]
requires: []
provides:
  - baseline Alembic schema management for Phase 1 tables
  - manifest-aware file-bundle ingestion driven by connector config
  - idempotent migration bootstrap for pre-Alembic local databases
affects: [phase-02, docker, local-ops]
tech-stack:
  added: [alembic]
  patterns:
    - migration-first database initialization outside in-memory tests
    - connector-config-driven ingestion instead of hardcoded manifest names
key-files:
  created:
    - alembic.ini
    - alembic/env.py
    - alembic/versions/0001_phase1_baseline.py
  modified:
    - pyproject.toml
    - src/ai_investing/persistence/db.py
    - src/ai_investing/ingestion/file_connectors.py
    - src/ai_investing/application/services.py
    - tests/test_ingestion.py
key-decisions:
  - "Use Alembic as the baseline schema path for non-test environments while keeping in-memory SQLite tests on metadata.create_all."
  - "Stamp existing local schemas at head when tables already exist but alembic_version does not, so init-db remains idempotent."
  - "Consume connector manifest_file from config instead of assuming manifest.json."
patterns-established:
  - "Migration bootstrap is safe for both fresh databases and legacy pre-migration Phase 1 databases."
  - "Connector metadata is part of the typed runtime contract, not decorative YAML."
requirements-completed: [COV-01, COV-02, ING-01, ING-02, MEM-01, MEM-02]
duration: recovery-session
completed: 2026-03-10
---

# Phase 01 Plan 02 Summary

**Phase 1 persistence now has a real Alembic baseline, connector-driven ingestion semantics, and an idempotent local database bootstrap path.**

## Performance

- **Duration:** recovery session
- **Started:** 2026-03-10T00:00:00Z
- **Completed:** 2026-03-10T02:43:47Z
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments

- Added Alembic configuration and a baseline migration for the Phase 1 schema.
- Updated database initialization to use migrations for real databases while preserving lightweight in-memory test setup.
- Made file ingestion honor connector `manifest_file` config and validated company-type compatibility at the service boundary.

## Task Commits

The executor handoff stalled before task-level commits were produced. Recovery execution continued directly in the workspace and verification was completed against the final working tree.

## Files Created/Modified

- `alembic.ini` / `alembic/env.py` / `alembic/versions/0001_phase1_baseline.py` - Established the migration baseline and runtime environment.
- `pyproject.toml` - Added Alembic to the project dependencies.
- `src/ai_investing/persistence/db.py` - Switched real database initialization to migrations and added legacy-schema stamping.
- `src/ai_investing/ingestion/file_connectors.py` - Consumed configurable manifest names and fixed mutable defaults.
- `src/ai_investing/application/services.py` - Hardened connector kind and company-type checks.
- `tests/test_ingestion.py` - Added manifest-file coverage for connector-driven ingestion.

## Decisions Made

- In-memory SQLite remains metadata-driven for test speed; non-test databases use migrations to avoid silent schema drift.
- Existing local schemas are stamped rather than recreated, because Phase 1 already had pre-Alembic tables in circulation.
- Connector manifest names stay config-driven so future adapters can vary without touching runtime code.

## Deviations from Plan

- The migration bootstrap needed an extra compatibility step for pre-Alembic developer databases after the initial runbook smoke test exposed duplicate-table failures.

## Issues Encountered

- The first Docker runbook attempt exited during startup because the Postgres volume contained an unstamped baseline schema. The database bootstrap was updated to stamp that case and rerun cleanly.

## User Setup Required

None.

## Next Phase Readiness

- Real database environments now have a safe Phase 1 schema path.
- Later phases can add migrations incrementally instead of depending on implicit table creation.

---
*Phase: 01-foundation-and-contracts*
*Completed: 2026-03-10*
