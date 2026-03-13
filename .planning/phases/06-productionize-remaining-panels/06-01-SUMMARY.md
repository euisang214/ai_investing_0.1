---
phase: 06-productionize-remaining-panels
plan: 01
subsystem: orchestration
tags: [langgraph, panel-rollout, memo, cli, api, generated-examples]
requires:
  - phase: 03-remaining-panel-scaffolds
    provides: scaffold panel registry, factor mappings, placeholder prompt seams
  - phase: 04-monitoring-and-connectors
    provides: connector-backed evidence families, monitoring deltas, portfolio read models
  - phase: 05-scheduling-and-notifications
    provides: auto-continue gatekeeper policy, queue-safe run lifecycle, generated lifecycle artifacts
provides:
  - config-driven rollout waves between weekly_default and full_surface
  - typed panel readiness and support contracts with weak-confidence and structured skip outcomes
  - shared channel-aware debate runtime with real lead execution and truthful partial-run memo wording
affects: [phase-06-follow-on-panels, monitoring, generated-examples, operator-surfaces]
tech-stack:
  added: []
  patterns:
    - config-driven panel rollout and per-run support evaluation
    - shared input-channel payload assembly for specialists, judges, and leads
    - explicit skipped-panel and support-assessment read surfaces
key-files:
  created:
    - .planning/phases/06-productionize-remaining-panels/06-01-SUMMARY.md
  modified:
    - config/panels.yaml
    - config/run_policies.yaml
    - src/ai_investing/application/services.py
    - src/ai_investing/config/models.py
    - src/ai_investing/domain/models.py
    - src/ai_investing/domain/read_models.py
    - src/ai_investing/graphs/subgraphs.py
    - prompts/memo_updates/section_update.md
    - prompts/ic/synthesizer.md
    - examples/generated/ACME/initial/result.json
key-decisions:
  - "Keep rollout policy and per-panel support gates entirely config-driven instead of adding panel-specific graph branches."
  - "Persist weak-confidence and skipped-panel outcomes as typed run metadata so API, CLI, memo projection, and generated examples all describe the same run posture."
  - "Keep parent requirement V2-01 open; this plan completes rollout slice V2-01A rather than all remaining panel productionization."
patterns-established:
  - "Panel support contract: readiness sets the normal bar, support sets company-type eligibility plus weak-confidence fallback."
  - "Truthful partial runs: memo and IC output must state pending or unsupported overlays rather than implying full-surface coverage."
requirements-completed: [V2-01A]
duration: 35min
completed: 2026-03-13
---

# Phase 6 Plan 01: Productionize Remaining Panels Summary

**Config-driven rollout waves, typed support gates, explicit skipped-panel reads, and truthful partial-run memo synthesis for the first remaining-panel production slice**

## Performance

- **Duration:** 35 min
- **Started:** 2026-03-13T20:24:59Z
- **Completed:** 2026-03-13T21:00:15Z
- **Tasks:** 3
- **Files modified:** 26

## Accomplishments
- Added rollout-wave policies and typed readiness/support config so implemented panels can be selected by policy without orchestration branching.
- Refactored the shared runtime to honor declared input channels, execute real lead prompts, and surface unsupported panels as typed skips in service, CLI, API, and persisted reads.
- Kept memo updates, IC synthesis, and generated lifecycle examples truthful when overlays are pending, unsupported, or operating under weak-confidence support.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add rollout policies and additive panel support configuration** - `7c300db` (`feat`)
2. **Task 2: Make panel execution honor shared input channels, real lead prompts, and explicit skip results** - `062df2e` (`feat`)
3. **Task 3: Make memo and IC synthesis truthful when panels are weak-confidence or skipped** - `a1cb5f2` (`feat`)
4. **Verification fixup: Harden weak-confidence gatekeeper verification** - `dd11310` (`fix`)

## Files Created/Modified

- `config/panels.yaml` - Added readiness/support contracts for every panel and enabled gatekeeper weak-confidence for thin connector slices.
- `config/run_policies.yaml` - Added intermediate rollout waves between `weekly_default` and `full_surface`.
- `src/ai_investing/application/services.py` - Added support evaluation, skip persistence, channel-aware payload assembly, lead execution, and truthful memo projection.
- `src/ai_investing/domain/models.py` - Added typed support-assessment and skipped-panel records.
- `src/ai_investing/domain/read_models.py` - Added stable panel read surfaces for verdict or skip results.
- `src/ai_investing/graphs/subgraphs.py` - Preserved panel state across memo updates so gatekeeper checkpoints still resolve from live graph state.
- `prompts/memo_updates/section_update.md` - Required section updates to mention weak-confidence support and skipped panels.
- `prompts/ic/synthesizer.md` - Required overall recommendation wording to stay explicit about pending or unsupported overlays.
- `examples/generated/ACME/*` - Regenerated lifecycle artifacts to reflect support assessments and truthful partial-run wording.

## Decisions Made

- Kept rollout and support behavior declarative in registry config so later Phase 6 plans can enable more panels without runtime branching.
- Treated weak-confidence as an additive posture over the same panel/verdict contract rather than inventing a separate runtime path.
- Preserved existing memo section ids and rerun delta behavior while making `overall_recommendation` explicitly call out pending or unsupported overlays.
- Left parent requirement `V2-01` open because this plan only delivers slice `V2-01A`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Added source-type fallback for support evaluation**
- **Found during:** Task 2
- **Issue:** Some seeded evidence fixtures did not populate `metadata.evidence_family`, which caused support checks to misclassify otherwise valid records.
- **Fix:** Derived evidence families from `source_type` when the explicit metadata field is absent.
- **Files modified:** `src/ai_investing/application/services.py`
- **Verification:** Task 2 targeted runtime tests plus final full-suite verification
- **Committed in:** `062df2e`

**2. [Rule 1 - Bug] Preserved truthful memo wording without breaking existing recommendation ordering**
- **Found during:** Task 3
- **Issue:** New weak-confidence and skipped-overlay notes could displace existing provisional wording and regress established memo semantics.
- **Fix:** Applied truthfulness notes in memo projection before the provisional prefix and added regressions for overlay-pending, overlay-unsupported, and weak-confidence text.
- **Files modified:** `src/ai_investing/application/services.py`, `tests/test_monitoring_semantics.py`
- **Verification:** Task 3 targeted memo tests plus final full-suite verification
- **Committed in:** `a1cb5f2`

**3. [Rule 1 - Bug] Hardened gatekeeper verification for thin connector-backed slices**
- **Found during:** Final full-suite verification
- **Issue:** Connector-backed public and private slices could classify `gatekeepers` out before checkpointing, and memo subgraph transitions could drop the live gatekeeper verdict state.
- **Fix:** Enabled a weak-confidence fallback for gatekeepers in config, preserved panel state across memo subgraphs, kept lead synthesis summaries stable under weak-confidence notes, and regenerated checked lifecycle artifacts.
- **Files modified:** `config/panels.yaml`, `src/ai_investing/application/services.py`, `src/ai_investing/graphs/subgraphs.py`, `src/ai_investing/providers/fake.py`, `tests/test_monitoring_semantics.py`, `tests/test_run_lifecycle.py`, `examples/generated/ACME/*`
- **Verification:** Targeted connector/generated-example tests, `docker compose run --rm api pytest -q`, and `docker compose run --rm api ruff check src tests`
- **Committed in:** `dd11310`

---

**Total deviations:** 3 auto-fixed (`Rule 1`: 3)
**Impact on plan:** All deviations were correctness fixes that kept the rollout contract truthful and reusable without changing the plan's scope.

## Issues Encountered

- Host Python remains below the repo target, so verification continued to rely on Docker-based commands.
- Checked-in generated lifecycle artifacts needed regeneration once support assessments and truthful partial-run wording became part of the runtime contract.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 6 now has the shared rollout contract needed to flip on additional panel families without introducing bespoke runtime branches.
- Follow-on Phase 6 plans can focus on panel-specific prompt, fixture, and agent productionization while reusing the shipped support, skip, memo, and operator surfaces from this slice.

## Self-Check: PASSED

- Verified `.planning/phases/06-productionize-remaining-panels/06-01-SUMMARY.md` exists.
- Verified task and fix commits `7c300db`, `062df2e`, `a1cb5f2`, and `dd11310` resolve locally.
