---
phase: 06-productionize-remaining-panels
plan: 07
status: complete
completed_by: gsd-agent
---

## One-liner

Closed the diagnostic expectations gap by folding `consensus`, `market`, and `events` evidence families into the default ACME manifests and reconciling test and generator seeding to the same contract.

## What changed

| File | Change |
|---|---|
| `examples/acme_public/manifest.json` | Added three documents: `consensus_snapshot` (family: consensus), `market_snapshot` (family: market), `catalyst_tracker` (family: events) — satisfying expectations panel requirements natively |
| `examples/acme_public_rerun/manifest.json` | Added `evidence_family: consensus` metadata to rerun Q1 update document |
| `tests/test_analysis_flow.py` | Removed 5 `_seed_public_expectations_connectors()` calls from default-path tests; rewrote unsupported expectations test to use intentionally limited `context` + wave2 connectors only |
| `tests/test_run_lifecycle.py` | Removed 2 bespoke connector calls; rewrote unsupported refresh test to use wave2-only fixture with proper imports |
| `scripts/generate_phase2_examples.py` | Removed `PUBLIC_EXPECTATIONS_CONNECTORS` constant and connector ingestion loop from `seed_acme()` |

## Gap closed

The default ACME `analyze_company("ACME")` under `expectations_rollout` now satisfies `expectations_catalyst_realization` requirements:

- `consensus_views` → `consensus` evidence family (from `consensus_snapshot` document)
- `market_data` → `market` evidence family (from `market_snapshot` document)
- `milestone_tracking` → `events` evidence family (from `catalyst_tracker` document)

## Not changed

- `config/panels.yaml` — expectations support gate unchanged
- `src/ai_investing/application/services.py` — evidence family aliases and resolution logic unchanged
- `tests/conftest.py` — `seeded_acme` fixture unchanged (inherits updated manifest)

## Unsupported path preserved

An explicit unsupported-expectations regression still exists, relocated to an intentionally limited fixture that uses wave2 connectors only (which supply market/regulatory/news evidence but tag none of it for `expectations_catalyst_realization`).

## Operator action required

After merging, regenerate checked artifacts:

```bash
python scripts/generate_phase2_examples.py
```

Then run verification:

```bash
pytest tests/test_analysis_flow.py tests/test_run_lifecycle.py tests/test_generated_examples.py -x -v
```
