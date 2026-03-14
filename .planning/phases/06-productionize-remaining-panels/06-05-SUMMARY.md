---
phase: 06-productionize-remaining-panels
plan: 05
subsystem: orchestration
tags: [overlay-wave, portfolio-context, recommendation-scope, full-surface, operator-surfaces]
requires:
  - phase: 06-01
    provides: rollout support rules, structured skips, and truthful partial-run memo wording
  - phase: 06-02
    provides: runnable Wave 1 company-quality panels and public/private support patterns
  - phase: 06-03
    provides: runnable Wave 2 external-context panels and rerun-safe lifecycle boundaries
  - phase: 06-04
    provides: runnable Wave 3 expectations coverage and regenerated expectation-aware artifacts
provides:
  - Runnable final-wave overlay panels that keep security/deal context and portfolio fit separate from company quality
  - Bounded `portfolio_context_summary` support for truthful portfolio-fit execution and explicit overlay skips
  - Operator-visible overall recommendation scope for overlay-complete versus company-quality-only runs
affects: [phase-06-closeout, generated-examples, operator-surfaces, memo-reconciliation]
tech-stack:
  added: []
  patterns:
    - config-driven overlay execution with strict support gating instead of bespoke graph branches
    - bounded portfolio-context evidence injection through a least-privilege tool surface
    - operator-visible recommendation scope that stays explicit when overlays skip
key-files:
  created: []
  modified:
    - config/panels.yaml
    - config/tool_registry.yaml
    - src/ai_investing/application/portfolio.py
    - src/ai_investing/application/services.py
    - src/ai_investing/tools/builtins.py
    - prompts/panels/security_overlay/panel_lead.md
    - prompts/panels/portfolio_fit/panel_lead.md
    - prompts/ic/synthesizer.md
    - src/ai_investing/api/main.py
    - src/ai_investing/cli.py
    - examples/generated/ACME/rerun/result.json
key-decisions:
  - "Keep `security_or_deal_overlay` and `portfolio_fit_positioning` as the final analytical wave and require explicit support context for each."
  - "Expose portfolio-fit inputs through a narrow reusable `portfolio_context_summary` seam instead of widening orchestration or tool access."
  - "Make API and CLI results state whether `overall_recommendation` is overlay-complete or company-quality-only when overlays are skipped."
patterns-established:
  - "Final-wave overlays can ship under the existing shared debate path as long as support and skip rules remain config-driven."
  - "Closeout verification for a newly runnable panel wave must include operator-surface tests and deterministic checked artifacts."
requirements-completed: [V2-01]
duration: 7h25m
completed: 2026-03-14
---

# Phase 6 Plan 05: Final overlay wave with bounded portfolio context and explicit recommendation scope

**Final-wave overlays now run as separate security/deal and portfolio-fit panels with bounded book-aware context and explicit company-quality-only recommendation wording when overlay support is missing.**

## Performance

- **Duration:** 7h25m elapsed, including the blocking human-verification checkpoint
- **Started:** 2026-03-14T05:28:46Z
- **Completed:** 2026-03-14T12:53:51Z
- **Tasks:** 4
- **Files modified:** 32

## Accomplishments

- Replaced the overlay placeholders with production config, full prompt suites, and strict support rules for `security_or_deal_overlay` and `portfolio_fit_positioning`.
- Added a narrow reusable portfolio-context seam so portfolio-fit work stays truthful and book-aware without widening orchestration.
- Locked API, CLI, memo, and IC wording to distinguish overlay-complete recommendations from company-quality-only results when overlays skip.
- Satisfied the blocking human-verification checkpoint with explicit approval of overlay separation, portfolio-context boundaries, and recommendation wording.

## Task Commits

Each task was committed atomically:

1. **Task 1: Replace overlay placeholders with production config and strict support rules** - `00bed71` (`feat`)
2. **Task 2: Add a narrow reusable portfolio-context seam and truthful overlay execution behavior** - `a54904f` (`feat`)
3. **Task 3: Lock operator surfaces to the final recommendation contract before closeout artifacts regenerate** - `fedacee` (`feat`)

Additional closeout verification cleanup: `6438667` (`fix`)

## Files Created/Modified

- `config/panels.yaml` - marks both overlay panels implemented and enforces strict support context requirements
- `config/tool_registry.yaml` - registers the narrow `portfolio_context_summary` surface
- `src/ai_investing/application/portfolio.py` - builds reusable, bounded portfolio summary inputs for overlay work
- `src/ai_investing/application/services.py` - threads overlay support posture and bounded portfolio context into runtime execution
- `src/ai_investing/tools/builtins.py` - exposes least-privilege portfolio-context access to panel agents
- `prompts/panels/security_overlay/*.md` - defines the production security/deal overlay debate and lead contracts
- `prompts/panels/portfolio_fit/*.md` - defines the production portfolio-fit and sizing debate and lead contracts
- `prompts/ic/synthesizer.md` - makes full versus company-quality-only recommendation wording explicit
- `src/ai_investing/api/main.py` - surfaces recommendation scope in API responses
- `src/ai_investing/cli.py` - surfaces recommendation scope in CLI output
- `examples/generated/ACME/*/result.json` - regenerated checked examples for the current persisted output contract

## Decisions Made

- Kept overlay execution on the shared config-driven runtime path instead of adding panel-specific graph branches.
- Required overlay support to be explicit and truthy rather than inferred from generic company-quality evidence.
- Treated user approval of overlay separation, portfolio-context narrowness, and recommendation wording as the blocking checkpoint completion signal.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated stale full-surface closeout coverage and regenerated checked ACME results**
- **Found during:** Final verification after the human-verification checkpoint
- **Issue:** Full-suite tests still expected `full_surface` to block before run creation, still treated Phase 6 as having scaffold-only panels, and checked generated examples no longer matched current persisted output.
- **Fix:** Rewrote the stale closeout regressions to assert runnable `full_surface` behavior with explicit overlay skips, removed scaffold-era expectations, and regenerated deterministic ACME result artifacts.
- **Files modified:** `tests/test_config_and_registry.py`, `tests/test_analysis_flow.py`, `tests/test_run_lifecycle.py`, `examples/generated/ACME/initial/result.json`, `examples/generated/ACME/continued/result.json`, `examples/generated/ACME/rerun/result.json`
- **Verification:** `docker compose run --rm api pytest -q`
- **Committed in:** `6438667`

**2. [Rule 3 - Blocking] Cleaned lint regressions in plan-owned overlay files**
- **Found during:** Final `ruff check src tests`
- **Issue:** The plan-owned overlay changes left long lines and import ordering violations in runtime and interface test files, which blocked the repo lint gate.
- **Fix:** Wrapped the affected service and test lines and normalized the CLI import block without changing behavior.
- **Files modified:** `src/ai_investing/application/services.py`, `tests/test_analysis_flow.py`, `tests/test_api.py`, `tests/test_cli.py`, `tests/test_run_lifecycle.py`
- **Verification:** `docker compose run --rm api ruff check src tests`
- **Committed in:** `6438667`

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Both fixes were direct fallout from making the overlay wave runnable and closing it out under the repo's full verification gate. No architectural scope increase was introduced.

## Issues Encountered

- The blocking checkpoint resumed cleanly with user approval, but final verification surfaced stale scaffold-era closeout coverage that still assumed `full_surface` was non-runnable.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 6 now has runnable coverage for every top-level panel, including the overlay wave, with truthful support and skip behavior across company-quality and overlay surfaces.
- API, CLI, memo, and IC outputs now expose whether `overall_recommendation` is overlay-complete or company-quality-only.
- Parent requirement `V2-01` is ready to remain marked complete while the remaining phase work can focus on closeout artifacts and any final archive/readiness tasks.

## Self-Check

PASSED - summary file exists and commits `00bed71`, `a54904f`, `fedacee`, and `6438667` resolve directly via `git rev-parse --verify`.
