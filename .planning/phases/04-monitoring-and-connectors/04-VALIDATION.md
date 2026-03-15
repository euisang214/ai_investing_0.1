---
phase: 4
slug: monitoring-and-connectors
status: ready
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-12
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + ruff |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `docker compose run --rm api pytest -q tests/test_config_and_registry.py tests/test_connector_runtime.py -k "connector or registry"` |
| **Full suite command** | `docker compose run --rm api pytest -q && docker compose run --rm api ruff check src tests` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run the task-level `verify` command from the active plan.
- **After Wave 1:** `04-01-PLAN.md` runs the full suite in its closing `<verification>` block before Wave 2 can begin.
- **After Wave 2 / before Wave 3 implementation:** `04-04-PLAN.md` Task 1 reruns the full suite as a blocking preflight because it depends on both Wave 2 plans.
- **After Wave 3 / before phase completion:** `04-04-PLAN.md` reruns the full suite in its closing `<verification>` block.
- **Before `$gsd-verify-work`:** The final full-suite gate must already be green.
- **Max feedback latency:** 30 seconds

Because `$gsd-execute-phase` has no standalone per-wave hook, wave-boundary suite checks are embedded in the last plan of a wave or the first plan that depends on the entire previous wave.

---

## Executable Wave Gates

| Wave Boundary | Enforced By | Automated Command | Why This Is Executable |
|---------------|-------------|-------------------|------------------------|
| After Wave 1 | `04-01-PLAN.md` `<verification>` | `docker compose run --rm api pytest -q && docker compose run --rm api ruff check src tests` | Wave 2 cannot start until the only Wave 1 plan completes. |
| After Wave 2 | `04-04-PLAN.md` Task 1 | `docker compose run --rm api pytest -q && docker compose run --rm api ruff check src tests` | `04-04` depends on both `04-02` and `04-03`, so Task 1 validates the merged Wave 2 state before Wave 3 edits. |
| After Wave 3 | `04-04-PLAN.md` `<verification>` | `docker compose run --rm api pytest -q && docker compose run --rm api ruff check src tests` | Final phase completion is blocked on a green full suite. |

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | V2-02 | unit | `docker compose run --rm api pytest -q tests/test_config_and_registry.py -k "connector or registry"` | ✅ | ⬜ pending |
| 04-01-02 | 01 | 1 | V2-02 | integration | `docker compose run --rm api pytest -q tests/test_connector_runtime.py tests/test_ingestion.py -k "connector or runtime or ingest"` | ❌ | ⬜ pending |
| 04-01-03 | 01 | 1 | V2-02 | regression | `docker compose run --rm api pytest -q tests/test_config_and_registry.py tests/test_connector_runtime.py` | ❌ | ⬜ pending |
| 04-02-01 | 02 | 2 | V2-02 | scope/docs | `docker compose run --rm api python -c "from pathlib import Path; docs = Path('docs/ingestion.md').read_text(encoding='utf-8').lower(); cfg = Path('config/source_connectors.yaml').read_text(encoding='utf-8').lower(); required = ['regulatory', 'market', 'consensus', 'ownership', 'dataroom']; missing = [item for item in required if item not in docs or item not in cfg]; assert not missing, missing; assert 'lightweight live public connector' in docs; assert 'attachment-only' in docs; assert 'pdf' in docs and 'spreadsheet' in docs"` | ❌ | ⬜ pending |
| 04-02-CP1 | 02 | 2 | V2-02 | checkpoint | Blocking `checkpoint:human-verify` in `04-02-PLAN.md` | ✅ | ⬜ pending |
| 04-02-02 | 02 | 2 | V2-02 | integration | `docker compose run --rm api pytest -q tests/test_ingestion.py tests/test_live_connector_runtime.py -k "public or connector or live or regulatory or consensus"` | ❌ | ⬜ pending |
| 04-02-03 | 02 | 2 | V2-02 | regression | `docker compose run --rm api pytest -q tests/test_ingestion.py tests/test_analysis_flow.py -k "ingest or evidence or dataroom or regulatory or consensus"` | ✅ | ⬜ pending |
| 04-03-01 | 03 | 2 | V2-04 | integration | `docker compose run --rm api pytest -q tests/test_monitoring_semantics.py tests/test_run_lifecycle.py -k "monitoring or drift or concentration"` | ✅ | ⬜ pending |
| 04-03-02 | 03 | 2 | V2-04 | integration | `docker compose run --rm api pytest -q tests/test_analog_graph.py tests/test_monitoring_semantics.py tests/test_run_lifecycle.py -k "analog or graph or contradiction or delta"` | ❌ | ⬜ pending |
| 04-03-03 | 03 | 2 | V2-04 | regression | `docker compose run --rm api pytest -q tests/test_monitoring_semantics.py tests/test_generated_examples.py tests/test_analog_graph.py` | ❌ | ⬜ pending |
| 04-04-01 | 04 | 3 | V2-04 | repository + wave gate | `docker compose run --rm api pytest -q && docker compose run --rm api ruff check src tests && docker compose run --rm api pytest -q tests/test_repository_semantics.py -k "monitoring or portfolio or watchlist"` | ✅ | ⬜ pending |
| 04-04-02 | 04 | 3 | V2-04 | api/cli | `docker compose run --rm api pytest -q tests/test_api.py tests/test_cli.py -k "delta or monitoring or portfolio or watchlist"` | ✅ | ⬜ pending |
| 04-04-CP1 | 04 | 3 | V2-04 | checkpoint | Blocking `checkpoint:human-verify` in `04-04-PLAN.md` | ✅ | ⬜ pending |
| 04-04-03 | 04 | 3 | V2-04 | docs/integration | `docker compose run --rm api python -c "from pathlib import Path; readme = Path('README.md').read_text(encoding='utf-8').lower(); arch = Path('docs/architecture.md').read_text(encoding='utf-8').lower(); memory = Path('docs/memory_model.md').read_text(encoding='utf-8').lower(); combined = '\\n'.join([readme, arch, memory]); required = ['portfolio_fit_positioning', 'read-only', 'monitoring history', 'portfolio monitoring', 'watchlist']; missing = [item for item in required if item not in combined]; assert not missing, missing"` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

`File Exists` reflects pre-execution reality. `❌` means the plan intentionally creates that file during execution.

---

## Wave 0 Requirements

- [x] Existing infrastructure covers all phase requirements.
- [x] `tests/test_ingestion.py` already provides the baseline ingestion contract seam to extend.
- [x] `tests/test_monitoring_semantics.py` already provides the baseline monitoring contract seam to extend.
- [x] Docker-based Python 3.11 validation already exists and should remain the execution default.

---

## Blocking Checkpoints

| Behavior | Plan Checkpoint | Requirement | Why Human Judgment Still Matters | Review Instructions |
|----------|-----------------|-------------|----------------------------------|---------------------|
| Review the chosen lightweight live public connector for scope discipline | `04-02-CP1` | V2-02 | Automated tests can validate transport seams and staleness tagging, but they cannot decide whether the chosen source stays lightweight enough for the repo's non-premium posture | Confirm the inventory still ships exactly one lightweight live public connector and does not imply broader live-system coverage than Phase 4 actually delivers. |
| Review the evidence-media policy for representativeness | `04-02-CP1` | V2-02 | Automated tests can prove extraction and attachment behavior, but they cannot judge whether the connector mix tells an honest story about first-class versus attachment-only evidence | Confirm PDFs and spreadsheets are first-class when feasible, HTML and images stay attachment-only by default, and required-system coverage is explicit rather than inferred. |
| Review the portfolio-summary boundary before finalizing the read surface | `04-04-CP1` | V2-04 | Automated tests can validate segmented read models, but they cannot enforce product-scope restraint or presentation emphasis by themselves | Confirm the summary is read-only, grouped by change type first, includes both portfolio and watchlist names by default, keeps those groups clearly separated, and elevates actionable shared-risk or overlap clusters into the main summary when present. |

---

## Validation Sign-Off

- [x] All auto tasks have executable `verify` commands, and all manual judgment points are encoded as blocking checkpoint tasks inside the plan set
- [x] Sampling continuity: no wave boundary reaches the next wave without an executable validation gate
- [x] Planned-but-missing Phase 4 test modules are explicitly marked as not yet present in the verification map
- [x] No watch-mode flags
- [x] Feedback latency < 180s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-03-12; revised 2026-03-13 for executable checkpoints and wave-gate alignment
