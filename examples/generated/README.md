# Generated Examples

These artifacts make the Phase 2 run lifecycle inspectable without running the app by hand.

## ACME

- `initial/`: the first `analyze_company("ACME")` result. `pass` and `review` now auto-continue, so `result.json` is already terminal, `delta.json` is present, and untouched sections remain `not_advanced` instead of reading as stale carry-forward.
- `continued/`: the same completed run reloaded from durable storage. This keeps the compatibility example for run inspection after completion without requiring a second execution path.
- `rerun/`: a later `refresh_company("ACME")` run after new evidence is ingested. This is the first place `delta.json` compares against a prior active run and where carried-forward memo sections may legitimately read as stale.

## BETA

- `BETA/private/`: the private-company sample output retained as a separate ingestion example.

## How To Inspect

1. Open `result.json` to inspect lifecycle fields, checkpoint state, and panel outputs.
2. Open `memo.md` to read the rendered memo state for that run.
3. Open `delta.json` to inspect the monitoring output and prior-run linkage.

## Regenerate

Run `docker compose run --rm api python scripts/generate_phase2_examples.py`.

If Python 3.11+ is available on the host, `python scripts/generate_phase2_examples.py` produces the same ACME artifacts.
