---
status: resolved
trigger: "In a policy that includes the expectations wave, the run should populate `expectations_variant_view` and `realization_path_catalysts` from supported evidence, and a rerun with changed expectation inputs should surface those changes in `what_changed_since_last_run` and the monitoring delta."
created: 2026-03-15T13:08:58Z
updated: 2026-03-15T14:16:16Z
---

## Current Focus

hypothesis: Confirmed: the default ACME seed and rerun manifests do not provide the full evidence-family contract required by expectations_catalyst_realization, while the passing tests/examples only succeed because they manually ingest supplemental connector packets first.
test: Static trace completed across panel readiness, support evaluation, seeded fixtures, expectations-specific tests, and the checked example generator.
expecting: N/A
next_action: Return diagnose-only result with the fixture/runtime contract mismatch and the paths that hide it.

## Symptoms

expected: `expectations_rollout` on ACME should advance `expectations_catalyst_realization` and refresh the expectations/catalyst memo sections.
actual: Both analyze and refresh left `expectations_catalyst_realization` unsupported for ACME due to missing evidence families (`consensus_views`, `market_data`, `milestone_tracking`), so `expectations_variant_view` and `realization_path_catalysts` stayed stale.
errors: None reported beyond unsupported/skip metadata.
reproduction: Test 5 in Phase 06 UAT.
started: Discovered during UAT after Phase 06 completion.

## Eliminated

## Evidence

- timestamp: 2026-03-15T13:12:00Z
  checked: config/panels.yaml and src/ai_investing/application/services.py
  found: expectations_catalyst_realization requires public evidence families consensus_views, market_data, and milestone_tracking; support evaluation marks the panel unsupported whenever those aliases are absent.
  implication: the panel will only run if ACME has consensus, market/news/ownership, and events evidence attached to that panel.

- timestamp: 2026-03-15T13:13:00Z
  checked: examples/acme_public/manifest.json
  found: the default ACME seed contains only regulatory/transcript-tagged records and no document targets expectations_catalyst_realization.
  implication: seeded ACME cannot satisfy the expectations rollout by default.

- timestamp: 2026-03-15T13:14:00Z
  checked: tests/conftest.py
  found: seeded_acme ingests only examples/acme_public before coverage is added.
  implication: any analyze/refresh flow that starts from the standard ACME fixture will miss the expectations evidence families unless extra ingestion happens elsewhere.

- timestamp: 2026-03-15T13:15:00Z
  checked: tests/test_analysis_flow.py and scripts/generate_phase2_examples.py
  found: the passing expectations tests and checked example generator first ingest acme_market_packet, acme_regulatory_packet, acme_transcript_news_packet, acme_consensus_packet, and acme_events_packet through dedicated helpers.
  implication: the repo's green expectations assertions depend on bespoke supplemental seeding, not on the default ACME fixture used by broader UAT.

- timestamp: 2026-03-15T13:16:00Z
  checked: examples/acme_public_rerun/manifest.json and connector manifests
  found: the rerun manifest adds transcript plus events only; the missing consensus and market evidence families come from the supplemental connector manifests, not from the base rerun packet.
  implication: rerun input alone cannot make expectations_catalyst_realization supported, so delta movement is impossible without the supplemental connectors already ingested.

## Resolution

root_cause: The expectations rollout contract is only satisfied in bespoke test/example setup that manually ingests supplemental consensus, market, and events connector packets. The standard ACME seed used by generic/UAT flows ingests only examples/acme_public, and the rerun fixture still does not supply the missing consensus and market families. As a result, expectations_catalyst_realization is truthfully evaluated as unsupported, leaving expectations_variant_view and realization_path_catalysts stale.
fix: Plan 06-07 folded consensus, market, and events evidence families into the default ACME baseline manifest and removed bespoke connector dependencies from tests and the generate script.
verification: 182/184 tests pass (2 pre-existing live_connector failures). All 9 expectations-related tests pass on the default ACME path.
files_changed:
  - examples/acme_public/manifest.json
  - examples/acme_public_rerun/manifest.json
  - tests/test_analysis_flow.py
  - tests/test_run_lifecycle.py
  - tests/test_monitoring_semantics.py
  - tests/test_ingestion.py
  - tests/test_connector_runtime.py
  - scripts/generate_phase2_examples.py
