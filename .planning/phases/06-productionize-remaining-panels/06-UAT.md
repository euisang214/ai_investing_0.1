---
status: diagnosed
phase: 06-productionize-remaining-panels
source:
  - .planning/phases/06-productionize-remaining-panels/06-01-SUMMARY.md
  - .planning/phases/06-productionize-remaining-panels/06-02-SUMMARY.md
  - .planning/phases/06-productionize-remaining-panels/06-03-SUMMARY.md
  - .planning/phases/06-productionize-remaining-panels/06-04-SUMMARY.md
  - .planning/phases/06-productionize-remaining-panels/06-05-SUMMARY.md
  - .planning/phases/06-productionize-remaining-panels/06-06-SUMMARY.md
started: 2026-03-14T13:20:17Z
updated: 2026-03-15T13:12:40Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: From a fully stopped stack with fresh ephemeral state, start the application using the documented Docker workflow. The stack should boot without startup errors, expose the API cleanly, and allow one primary check such as a health request or a basic analysis command without missing-mount surprises from the Phase 6 closeout changes.
result: pass

### 2. Weekly Default Truthfulness
expected: Run a normal `weekly_default` analysis for a sample company. The result should complete without pretending every panel ran, and the memo, CLI, or API output should explicitly describe any pending, skipped, unsupported, or weak-confidence surfaces instead of implying full-surface coverage.
result: pass

### 3. Wave 1 Company-Quality Panels
expected: In a policy that includes the internal company-quality wave, the run should now produce real outcomes for supply or product operations, management or governance, and financial quality. Those panel results should appear as executed work with support posture and section-scoped memo updates, not scaffold rejections.
result: pass

### 4. Wave 2 External-Context Panels
expected: In a policy that includes external company-quality work, market structure or growth, macro or industry transmission, and external regulatory should run with visible evidence-backed results. On rerun, the resulting memo and delta output should stay scoped to the affected external-company-quality sections rather than mutating unrelated sections.
result: pass

### 5. Expectations and Catalyst Rollout
expected: In a policy that includes the expectations wave, the run should populate `expectations_variant_view` and `realization_path_catalysts` from supported evidence. A rerun with changed expectation inputs should surface those changes in `what_changed_since_last_run` and the monitoring delta instead of silently burying them.
result: issue
reported: "The `expectations_rollout` policy included `expectations_catalyst_realization`, but both analyze and refresh left it unsupported for ACME due to missing evidence families (`consensus_views`, `market_data`, `milestone_tracking`), so `expectations_variant_view` and `realization_path_catalysts` stayed stale instead of being populated."
severity: major

### 6. Overlay Recommendation Scope
expected: In a `full_surface` style run, security or deal overlay and portfolio-fit positioning should execute when supported and skip explicitly when not. The final recommendation wording should clearly distinguish overlay-complete output from company-quality-only output, and any portfolio-fit context used should remain bounded rather than leaking broad portfolio data.
result: pass

### 7. Generated Example and Docs Contract
expected: The checked docs and generated examples should match the shipped runtime contract. In particular, the repo docs should describe the finished Phase 6 panel surface truthfully, and the `examples/generated/ACME/overlay_gap` artifacts should visibly show an explicit unsupported-overlay outcome while the rest of the company-quality analysis still completes.
result: pass

## Summary

total: 7
passed: 6
issues: 1
pending: 0
skipped: 0

## Gaps

- truth: "In a policy that includes the expectations wave, the run should populate `expectations_variant_view` and `realization_path_catalysts` from supported evidence, and a rerun with changed expectation inputs should surface those changes in `what_changed_since_last_run` and the monitoring delta."
  status: failed
  reason: "User reported: The `expectations_rollout` policy included `expectations_catalyst_realization`, but both analyze and refresh left it unsupported for ACME due to missing evidence families (`consensus_views`, `market_data`, `milestone_tracking`), so `expectations_variant_view` and `realization_path_catalysts` stayed stale instead of being populated."
  severity: major
  test: 5
  root_cause: "The expectations panel support gate is correct, but the default ACME analyze/refresh fixture contract is incomplete. `expectations_catalyst_realization` requires public evidence families `consensus_views`, `market_data`, and `milestone_tracking`; the standard ACME public manifests used by normal analyze/refresh flows do not provide the needed expectations evidence, while the passing tests and generated examples only succeed because they preload supplemental connector packets."
  artifacts:
    - path: "config/panels.yaml"
      issue: "Expectations panel requires `consensus_views`, `market_data`, and `milestone_tracking` for public support."
    - path: "src/ai_investing/application/services.py"
      issue: "Support evaluation correctly marks the panel unsupported when those evidence families are absent."
    - path: "examples/acme_public/manifest.json"
      issue: "Default ACME public fixture lacks the expectations evidence families needed for `expectations_rollout`."
    - path: "examples/acme_public_rerun/manifest.json"
      issue: "Rerun fixture adds some expectations factors and events but still does not provide the full consensus and market support contract."
    - path: "tests/test_analysis_flow.py"
      issue: "Supported expectations-path tests preload supplemental connector packets, which hides the default fixture gap."
    - path: "scripts/generate_phase2_examples.py"
      issue: "Generated examples also rely on bespoke supplemental connector ingestion rather than the default ACME analyze/refresh seed."
  missing:
    - "Align the default ACME public and rerun fixture contract with the expectations panel support requirements."
    - "Either ingest the supplemental expectations connector packets in the standard ACME expectations-rollout path or fold equivalent evidence into the default ACME manifests."
    - "Add regression coverage that exercises `expectations_rollout` through the same default ACME analyze/refresh path used in UAT."
  debug_session: ".planning/debug/acme-expectations-wave-stale.md"
