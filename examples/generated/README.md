# Generated Examples

These artifacts make the current run lifecycle inspectable without running the app by hand.

The checked ACME files now reflect the post-Phase-5 contract:

- every run still enters the `gatekeepers` checkpoint first
- `pass` and `review` auto-continue into downstream work
- `fail` would stop in the review queue and require an explicit operator-only provisional override
- the checkpoint record remains in `result.json` for auditability even when no human resume step is required

## ACME

- `initial/`: the first `analyze_company("ACME")` result. `result.json` is already terminal because the gatekeeper checkpoint resolves automatically for the generated `review` verdict. `delta.json` is present, and untouched sections remain `not_advanced` instead of reading as stale carry-forward.
- `continued/`: the same completed run reloaded from durable storage. This keeps the compatibility example for run inspection after completion without inventing a fake manual resume path.
- `rerun/`: a later `refresh_company("ACME")` run after new evidence is ingested. This is the first place `delta.json` compares against a prior active run and where carried-forward memo sections may legitimately read as stale.

The ACME set does not include a failed gatekeeper branch because that path is operationally different:

- the run would remain `awaiting_continue`
- the queue job would become `review_required`
- an immediate notification would be emitted
- only an operator could trigger `continue_provisional`

## BETA

- `BETA/private/`: the private-company sample output retained as a separate ingestion example.

## How To Inspect

1. Open `result.json` to inspect lifecycle fields, checkpoint state, and panel outputs.
2. Open `memo.md` to read the rendered memo state for that run.
3. Open `delta.json` to inspect the monitoring output and prior-run linkage.
4. Compare `initial/` and `continued/` to see the same completed run as returned live and as reloaded from persistence.
5. Compare `continued/` and `rerun/` to inspect the first true delta against a prior active memo.

## Regenerate

Run `docker compose run --rm api python scripts/generate_phase2_examples.py`.

If Python 3.11+ is available on the host, `python scripts/generate_phase2_examples.py` produces the same ACME artifacts.

The script keeps its historical name for compatibility with existing docs and tests, but it now regenerates the post-Phase-5 lifecycle examples rather than the retired universal-pause story.
