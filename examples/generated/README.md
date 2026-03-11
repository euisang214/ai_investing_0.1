# Generated Examples

These artifacts make the Phase 2 checkpoint flow inspectable without running the app by hand.

## ACME

- `initial/`: the first `analyze_company("ACME")` result. The run pauses after `gatekeepers`, `result.json` shows `awaiting_continue`, `memo.md` is partial, and `delta.json` is `null` because monitoring has not run yet.
- `continued/`: the same run after `continue_run(..., continue)`. This shows the downstream `demand_revenue_quality` panel, the reconciled memo, and the initial monitoring delta.
- `rerun/`: a later `refresh_company("ACME")` run after new evidence is ingested and the operator explicitly continues past the checkpoint again. `delta.json` is the materiality-aware rerun delta against the prior active run.

## BETA

- `BETA/private/`: the private-company sample output retained as a separate ingestion example.

## How To Inspect

1. Open `result.json` to inspect lifecycle fields, checkpoint state, and panel outputs.
2. Open `memo.md` to read the rendered memo state for that run.
3. Open `delta.json` to inspect the monitoring output. A value of `null` means the run stopped before monitoring executed.

## Regenerate

Run `docker compose run --rm api python scripts/generate_phase2_examples.py`.

If Python 3.11+ is available on the host, `python scripts/generate_phase2_examples.py` produces the same ACME artifacts.
