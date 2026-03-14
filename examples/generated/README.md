# Generated Examples

These checked artifacts document the shipped Phase 6 runtime contract, not a hypothetical happy path.

The ACME example set demonstrates four distinct outcomes:

- `initial/`: an initial `expectations_rollout` run
- `continued/`: the same completed run reloaded from persistence
- `rerun/`: a later refresh that produces a real delta against the prior active memo
- `overlay_gap/`: a `full_surface` run where company-quality and expectations analysis still complete, but `security_or_deal_overlay` and `portfolio_fit_positioning` are unsupported and skipped explicitly

## What These Files Prove

- every run still enters `gatekeepers`
- `pass` and `review` auto-continue into downstream work
- reruns keep delta behavior against the prior active memo
- rollout policies widen the selected panel surface without changing runtime shape
- unsupported overlays do not fail the whole run
- skipped overlays remain visible in `result.json` and in memo wording
- `overall_recommendation` stays scoped to the analysis that actually ran

## ACME

### `initial/`

Initial output for `expectations_rollout`.

- company-quality panels run
- `expectations_catalyst_realization` runs
- overlays are not selected by policy
- `overall_recommendation` should read as company-quality plus expectations, with overlay work still pending for that rollout

### `continued/`

Persisted reread of the same completed run.

- preserves the same `run_id`
- proves the completed run can be rehydrated without inventing a manual resume path
- keeps the same support posture visible after persistence

### `rerun/`

Refresh output after new evidence is ingested.

- `delta.json` compares against the prior active memo
- `what_changed_since_last_run` is updated
- expectations sections change in a way the regression suite can lock

### `overlay_gap/`

Initial output for `full_surface` without overlay-specific or portfolio context.

- company-quality and expectations work still complete honestly
- `security_or_deal_overlay` is selected but skipped with `status: unsupported`
- `portfolio_fit_positioning` is selected but skipped with `status: unsupported`
- the memo keeps those overlays visible as unsupported for this run rather than silently dropping them

## How To Inspect

1. Open `result.json` to inspect checkpoint state, support posture, skipped panels, and selected policy.
2. Open `memo.md` to inspect the rendered memo and how `overall_recommendation` describes pending or unsupported overlays.
3. Open `delta.json` to inspect rerun behavior.
4. Compare `initial/` and `continued/` for the same run live versus persisted.
5. Compare `rerun/` with `initial/` for delta behavior.
6. Compare `overlay_gap/` with `initial/` to see the difference between overlays not selected by policy and overlays selected but skipped explicitly.

## Regenerate

Run:

```bash
docker compose run --rm api python scripts/generate_phase2_examples.py
docker compose run --rm api pytest -q tests/test_generated_examples.py
```

If Python 3.11+ is available locally, `python scripts/generate_phase2_examples.py` produces the same artifacts.
