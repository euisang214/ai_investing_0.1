---
phase: 06-productionize-remaining-panels
plan: 04
subsystem: orchestration
tags: [wave-3, expectations, catalysts, rerun-delta, generated-examples]
requires:
  - phase: 06-01
    provides: rollout support rules, structured skips, and truthful partial-run memo wording
  - phase: 06-02
    provides: runnable Wave 1 company-quality panels and public/private support patterns
  - phase: 06-03
    provides: runnable Wave 2 external-context panels and rerun-safe lifecycle boundaries
provides:
  - Runnable `expectations_catalyst_realization` panel with bounded tools and production prompt contracts
  - Public and private expectations fixtures with explicit supported and skipped rollout behavior
  - Rerun-aware ACME artifacts where expectation and catalyst changes flow into delta output
affects: [phase-06-wave-4, generated-examples, monitoring-deltas, rollout-policies]
tech-stack:
  added: []
  patterns:
    - config-driven wave rollout with bounded panel-specific tool bundles
    - evidence-family support gating instead of bespoke runtime branches
    - Docker-regenerated golden artifacts after fixture and policy changes
key-files:
  created:
    - prompts/panels/expectations_catalyst_realization/advocate.md
    - prompts/panels/expectations_catalyst_realization/panel_lead.md
    - examples/connectors/acme_consensus_packet/acme_estimate_revision_context.md
    - examples/connectors/acme_events_packet/acme_catalyst_tracker.html
    - examples/beta_private/beta_milestone_tracker.md
  modified:
    - config/panels.yaml
    - config/agents.yaml
    - config/tool_bundles.yaml
    - examples/connectors/acme_consensus_packet/manifest.json
    - examples/connectors/acme_events_packet/manifest.json
    - scripts/generate_phase2_examples.py
    - tests/test_analysis_flow.py
    - tests/test_monitoring_semantics.py
    - tests/test_generated_examples.py
    - examples/generated/ACME/rerun/result.json
key-decisions:
  - "Keep `expectations_catalyst_realization` in the dedicated Wave 3 rollout and give it a bounded expectations-only research bundle."
  - "Use evidence-family readiness plus explicit skips for expectations support instead of introducing a new runtime-only `expectations_context` source."
  - "Regenerate checked ACME artifacts from the `expectations_rollout` policy so rerun deltas prove expectation-section movement in shipped examples."
patterns-established:
  - "Expectations-family panels should publish memo-section, factor, and provenance rules directly in markdown prompt contracts."
  - "When rollout policy changes alter checked artifacts, regenerate them through the shipped service entrypoints before declaring the contract green."
requirements-completed: [V2-01]
duration: 24min
completed: 2026-03-14
---

# Phase 6 Plan 04: Wave 3 expectations rollout, truthful support coverage, and rerun artifacts

**Wave 3 now runs `expectations_catalyst_realization` with real prompts, bounded evidence inputs, explicit skip behavior, and rerun artifacts that surface expectation-driven delta changes.**

## Performance

- **Duration:** 24 min
- **Started:** 2026-03-14T04:51:58Z
- **Completed:** 2026-03-14T05:16:34Z
- **Tasks:** 3
- **Files modified:** 36

## Accomplishments

- Replaced the expectations scaffold with a production agent stack, Wave 3 prompt suite, and bounded expectations/catalyst tool bundle.
- Expanded public and private fixtures so expectations support is truthful when consensus or milestone grounding exists and explicit when it does not.
- Regenerated ACME golden artifacts and added rerun regressions that prove expectation and catalyst changes flow into `what_changed_since_last_run` without implying overlay work is done.

## Task Commits

Each task was committed atomically:

1. **Task 1: Replace the expectations placeholder with a real prompt and agent stack** - `2c75bde` (`feat`)
2. **Task 2: Add expectations and milestone fixtures with explicit skip coverage** - `5be7006` (`feat`)
3. **Task 3: Extend rerun, delta, and generated artifact coverage for expectation shifts** - `3d12f8e` (`feat`)

Additional blocking full-suite cleanup: `c585401` (`fix`)

## Files Created/Modified

- `config/panels.yaml` - marks the expectations panel implemented and removes the impossible runtime-only context gate
- `config/agents.yaml` - adds the Wave 3 advocate, skeptic, durability, judge, and lead agent stack
- `config/tool_bundles.yaml` - narrows expectations work to evidence, claims, revisions, and catalyst-calendar inputs
- `prompts/panels/expectations_catalyst_realization/*.md` - defines the production prompt contract for variant view and realization-path synthesis
- `examples/connectors/acme_consensus_packet/manifest.json` - adds public consensus and market-grounding coverage for expectations
- `examples/connectors/acme_events_packet/manifest.json` - adds public catalyst and milestone-tracking coverage
- `examples/beta_private/manifest.json` - adds private milestone-style support for the expectations rollout
- `scripts/generate_phase2_examples.py` - drives checked ACME examples through the expectations rollout policy
- `tests/test_analysis_flow.py` - locks supported, skipped, and rerun expectations behavior
- `tests/test_monitoring_semantics.py` - locks expectation-section delta behavior
- `tests/test_generated_examples.py` - locks generated expectations coverage and checked artifact expectations
- `examples/generated/ACME/*` - regenerated deterministic ACME artifacts with expectation and catalyst deltas

## Decisions Made

- Kept the expectations rollout config-driven and additive by reusing the shared debate path instead of adding any panel-specific orchestration.
- Treated consensus, market, and milestone evidence families as the truthfulness gate for public expectations work, and dataroom plus milestone evidence as the private counterpart.
- Regenerated checked artifacts from the production service path rather than hand-editing examples so the repo contract stays inspectable.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Removed an impossible `expectations_context` readiness gate**
- **Found during:** Task 2 verification
- **Issue:** The plan inherited a required context key that the runtime never populates, which would force `expectations_catalyst_realization` to skip even when evidence support was sufficient.
- **Fix:** Removed the `required_context` entry and relied on the existing evidence-family and factor-coverage support checks for truthful support vs skip decisions.
- **Files modified:** `config/panels.yaml`, `tests/test_config_and_registry.py`
- **Verification:** `docker compose run --rm api pytest -q tests/test_analysis_flow.py tests/test_run_lifecycle.py -k "expectation or catalyst or skip"`
- **Committed in:** `5be7006`

**2. [Rule 3 - Blocking] Aligned full-suite expectations after the Wave 3 rollout changed fixture counts and checked artifacts**
- **Found during:** Final verification
- **Issue:** API/CLI full-surface tests still referenced the old scaffold blocker, ingestion tests still expected the pre-Wave-3 fixture counts, and generated-example assertions still reflected the old memo labels.
- **Fix:** Updated those contract tests to the new runnable expectations surface and regenerated checked ACME artifacts before rerunning the full gate.
- **Files modified:** `tests/test_api.py`, `tests/test_cli.py`, `tests/test_generated_examples.py`, `tests/test_ingestion.py`, `tests/test_run_lifecycle.py`
- **Verification:** `docker compose run --rm api pytest -q` and `docker compose run --rm api ruff check src tests`
- **Committed in:** `c585401`

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Both fixes were direct fallout from productionizing the Wave 3 expectations surface. No architectural expansion or scope creep was introduced.

## Issues Encountered

- Full-suite verification surfaced stale test assumptions from the former scaffold state and older fixture counts; they were updated immediately and reverified.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Wave 3 expectations and catalyst reasoning is now runnable, support-aware, and rerun-safe for both public and private sample companies.
- Checked ACME artifacts now show expectation-driven changes in `expectations_variant_view` and `realization_path_catalysts`.
- Phase 6 remains in progress because the overlay wave (`security_or_deal_overlay`, `portfolio_fit_positioning`) is still pending.


## Self-Check

PASSED - summary file exists and commits `2c75bde`, `5be7006`, `3d12f8e`, and `c585401` resolve as commits.
