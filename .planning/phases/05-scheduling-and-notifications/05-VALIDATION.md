---
phase: 5
slug: scheduling-and-notifications
status: ready
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-13
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + ruff |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `docker compose run --rm api pytest -q tests/test_config_and_registry.py tests/test_analysis_flow.py tests/test_run_lifecycle.py -k "cadence or due or queue or worker or notification"` |
| **Full suite command** | `docker compose run --rm api pytest -q && docker compose run --rm api ruff check src tests` |
| **Estimated runtime** | ~35 seconds |

---

## Sampling Rate

- **After every task commit:** Run the task-level `verify` command from the active plan.
- **After every plan wave:** Run `docker compose run --rm api pytest -q && docker compose run --rm api ruff check src tests`.
- **Before `$gsd-verify-work`:** The full suite must already be green.
- **Max feedback latency:** 35 seconds

Because Phase 5 introduces scheduling and worker state that can regress existing checkpoint semantics, every wave ends with an executable suite gate rather than a docs-only sign-off.

---

## Executable Wave Gates

| Wave Boundary | Enforced By | Automated Command | Why This Is Executable |
|---------------|-------------|-------------------|------------------------|
| After Wave 1 | `05-01-PLAN.md` `<verification>` | `docker compose run --rm api pytest -q && docker compose run --rm api ruff check src tests` | Wave 2 worker work should begin only after cadence-policy compatibility is validated. |
| After Wave 2 | `05-02-PLAN.md` `<verification>` | `docker compose run --rm api pytest -q && docker compose run --rm api ruff check src tests` | Wave 3 docs and n8n examples must describe the actual merged queue and notification behavior, not a speculative surface. |
| After Wave 3 | `05-03-PLAN.md` `<verification>` | `docker compose run --rm api pytest -q && docker compose run --rm api ruff check src tests` | Final phase completion is blocked on a green full suite plus checked examples and docs. |

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | V2-03 | registry | `docker compose run --rm api pytest -q tests/test_config_and_registry.py -k "cadence or schedule"` | ❌ | ⬜ pending |
| 05-01-02 | 01 | 1 | V2-03 | integration | `docker compose run --rm api pytest -q tests/test_analysis_flow.py tests/test_run_lifecycle.py -k "cadence or next_run_at or due"` | ✅ | ⬜ pending |
| 05-01-03 | 01 | 1 | V2-03 | api/cli | `docker compose run --rm api pytest -q tests/test_api.py tests/test_cli.py -k "coverage or cadence or next-run"` | ✅ | ⬜ pending |
| 05-02-01 | 02 | 2 | V2-05 | repository | `docker compose run --rm api pytest -q tests/test_repository_semantics.py -k "queue or worker or notification"` | ✅ | ⬜ pending |
| 05-02-02 | 02 | 2 | V2-05 | service | `docker compose run --rm api pytest -q tests/test_worker_runtime.py tests/test_run_lifecycle.py tests/test_analysis_flow.py` | ❌ | ⬜ pending |
| 05-02-03 | 02 | 2 | V2-05 | api/cli | `docker compose run --rm api pytest -q tests/test_api.py tests/test_cli.py -k "enqueue or worker or notification"` | ✅ | ⬜ pending |
| 05-03-01 | 03 | 3 | V2-03 | docs/examples | `docker compose run --rm api python -c "from pathlib import Path; files = [Path('README.md'), Path('docs/architecture.md'), Path('docs/runbook.md')]; text = '\\n'.join(path.read_text(encoding='utf-8').lower() for path in files); required = ['worker', 'notification', 'checkpoint', 'cadence']; missing = [item for item in required if item not in text]; assert not missing, missing" && docker compose run --rm api pytest -q tests/test_generated_examples.py` | ✅ | ⬜ pending |
| 05-03-02 | 03 | 3 | V2-03, V2-05 | fixture validation | `docker compose run --rm api python -c "import json; from pathlib import Path; names = ['weekly_watchlist_refresh.json', 'weekly_portfolio_refresh.json', 'new_evidence_webhook.json', 'refresh_notification.json']; payloads = [json.loads((Path('n8n') / name).read_text(encoding='utf-8')) for name in names]; assert all('nodes' in payload and payload['nodes'] for payload in payloads); assert all('connections' in payload for payload in payloads); readme = Path('n8n/README.md').read_text(encoding='utf-8').lower(); required = ['n8n', 'webhook', 'notification', 'queue', 'provisional']; missing = [item for item in required if item not in readme]; assert not missing, missing"` | ✅ | ⬜ pending |
| 05-03-CP1 | 03 | 3 | V2-03, V2-05 | checkpoint | Blocking `checkpoint:human-verify` in `05-03-PLAN.md` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

`File Exists` reflects pre-execution reality. `❌` means the plan intentionally creates that file during execution.

---

## Wave 0 Requirements

- [x] Existing pytest and ruff infrastructure can validate Phase 5 work.
- [x] `tests/test_analysis_flow.py`, `tests/test_run_lifecycle.py`, `tests/test_api.py`, and `tests/test_cli.py` already cover the current scheduling and checkpoint seams that Phase 5 must preserve.
- [x] Docker-based Python 3.11 verification already exists and remains the default execution path.

---

## Blocking Checkpoints

| Behavior | Plan Checkpoint | Requirement | Why Human Judgment Still Matters | Review Instructions |
|----------|-----------------|-------------|----------------------------------|---------------------|
| Review the external-automation boundary before finalizing docs and workflow examples | `05-03-CP1` | V2-03, V2-05 | Automated checks can prove files parse and docs mention the right terms, but they cannot decide whether the examples still keep n8n outside the reasoning runtime or whether failed-gatekeeper review behavior is honestly described | Confirm the refreshed `n8n/` workflows and docs show n8n scheduling, webhook intake, and notification delivery only; keep reasoning and provisional override logic inside the service; and describe pass or review auto-continuation plus fail-to-review-queue behavior accurately. |

---

## Validation Sign-Off

- [x] All auto tasks have executable `verify` commands, and the only manual judgment point is encoded as a blocking checkpoint inside the plan set.
- [x] Sampling continuity: every wave ends with an executable full-suite gate.
- [x] Planned-but-missing Phase 5 test modules are explicitly marked as not yet present in the verification map.
- [x] No watch-mode flags.
- [x] Feedback latency < 180s.
- [x] `nyquist_compliant: true` set in frontmatter.

**Approval:** approved 2026-03-13
