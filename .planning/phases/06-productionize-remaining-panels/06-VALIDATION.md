---
phase: 6
slug: productionize-remaining-panels
status: ready
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-13
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + ruff |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `docker compose run --rm api pytest -q tests/test_config_and_registry.py tests/test_analysis_flow.py tests/test_run_lifecycle.py tests/test_monitoring_semantics.py -k "panel or policy or memo or delta or skip or overlay"` |
| **Full suite command** | `docker compose run --rm api pytest -q && docker compose run --rm api ruff check src tests` |
| **Estimated runtime** | ~45 seconds |

---

## Sampling Rate

- **After every task commit:** Run the task-level `verify` command from the active plan.
- **After every wave boundary:** Run `docker compose run --rm api pytest -q && docker compose run --rm api ruff check src tests`.
- **Before `$gsd-verify-work`:** The full suite must already be green.
- **Max feedback latency:** 45 seconds

Because Phase 6 changes runnable panel surface area and memo truthfulness semantics, every wave needs an executable suite gate before the next wave adds more panels.

---

## Executable Wave Gates

| Wave Boundary | Enforced By | Automated Command | Why This Is Executable |
|---------------|-------------|-------------------|------------------------|
| After Wave 0 foundation | Final task of the Wave 0 plan set | `docker compose run --rm api pytest -q && docker compose run --rm api ruff check src tests` | Later panel work depends on the new support and skip contract being stable first. |
| After Wave 1 internal company-quality panels | Final task of the Wave 1 plan set | `docker compose run --rm api pytest -q && docker compose run --rm api ruff check src tests` | Wave 2 should build on merged runtime plus truthful internal-panel fixtures, not speculative seams. |
| After Wave 2 external company-quality panels | Final task of the Wave 2 plan set | `docker compose run --rm api pytest -q && docker compose run --rm api ruff check src tests` | Expectations and overlay work depend on the external-context coverage and skip behavior already being truthful. |
| After Wave 3 expectations/catalysts | Final task of the Wave 3 plan set | `docker compose run --rm api pytest -q && docker compose run --rm api ruff check src tests` | Overlay work must inherit the correct rerun and variant-view semantics. |
| After Wave 4 overlays / before phase completion | Closing `<verification>` of the final plan | `docker compose run --rm api pytest -q && docker compose run --rm api ruff check src tests` | Final phase completion is blocked on a green full suite with regenerated checked artifacts. |

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 0 | V2-01 | registry/runtime | `docker compose run --rm api pytest -q tests/test_config_and_registry.py tests/test_analysis_flow.py -k "panel or policy or implemented"` | ✅ | ⬜ pending |
| 06-01-02 | 01 | 0 | V2-01 | service skip semantics | `docker compose run --rm api pytest -q tests/test_run_lifecycle.py tests/test_analysis_flow.py -k "skip or unsupported or panel"` | ❌ | ⬜ pending |
| 06-01-03 | 01 | 0 | V2-01 | memo/ic truthfulness | `docker compose run --rm api pytest -q tests/test_monitoring_semantics.py tests/test_analysis_flow.py -k "memo or overall_recommendation or overlay"` | ✅ | ⬜ pending |
| 06-02-01 | 02 | 1 | V2-01 | prompt/registry inventory | `docker compose run --rm api pytest -q tests/test_config_and_registry.py tests/test_prompt_assets.py -k "supply or management or financial"` | ✅ | ⬜ pending |
| 06-02-02 | 02 | 1 | V2-01 | public/private truthfulness | `docker compose run --rm api pytest -q tests/test_analysis_flow.py tests/test_run_lifecycle.py tests/test_generated_examples.py -k "supply or management or financial"` | ❌ | ⬜ pending |
| 06-02-03 | 02 | 1 | V2-01 | api/cli | `docker compose run --rm api pytest -q tests/test_api.py tests/test_cli.py -k "panel or memo or policy or skip"` | ✅ | ⬜ pending |
| 06-03-01 | 03 | 2 | V2-01 | prompt/registry inventory | `docker compose run --rm api pytest -q tests/test_config_and_registry.py tests/test_prompt_assets.py -k "market or macro or regulatory"` | ✅ | ⬜ pending |
| 06-03-02 | 03 | 2 | V2-01 | external-context truthfulness | `docker compose run --rm api pytest -q tests/test_analysis_flow.py tests/test_run_lifecycle.py tests/test_generated_examples.py -k "market or macro or regulatory or weak"` | ❌ | ⬜ pending |
| 06-04-01 | 04 | 3 | V2-01 | rerun/delta semantics | `docker compose run --rm api pytest -q tests/test_monitoring_semantics.py tests/test_analysis_flow.py tests/test_run_lifecycle.py -k "expectation or catalyst or delta or rerun"` | ✅ | ⬜ pending |
| 06-04-02 | 04 | 3 | V2-01 | generated artifacts | `docker compose run --rm api pytest -q tests/test_generated_examples.py -k "expectation or catalyst or delta"` | ❌ | ⬜ pending |
| 06-05-01 | 05 | 4 | V2-01 | overlay support rules | `docker compose run --rm api pytest -q tests/test_analysis_flow.py tests/test_run_lifecycle.py tests/test_monitoring_semantics.py -k "overlay or portfolio or skip"` | ✅ | ⬜ pending |
| 06-05-02 | 05 | 4 | V2-01 | api/cli + artifacts | `docker compose run --rm api pytest -q tests/test_api.py tests/test_cli.py tests/test_generated_examples.py -k "overlay or portfolio or recommendation"` | ❌ | ⬜ pending |
| 06-05-CP1 | 05 | 4 | V2-01 | checkpoint | Blocking `checkpoint:human-verify` in the final overlay plan | ✅ | ⬜ pending |
| 06-06-01 | 06 | 4 | V2-01 | docs/examples | `docker compose run --rm api python -c "from pathlib import Path; files = [Path('README.md'), Path('docs/architecture.md'), Path('docs/runbook.md'), Path('docs/factor_ontology.md')]; text = '\\n'.join(path.read_text(encoding='utf-8').lower() for path in files); required = ['supply_product_operations', 'market_structure_growth', 'security_or_deal_overlay', 'portfolio_fit_positioning', 'skip', 'weak confidence', 'overall recommendation']; missing = [item for item in required if item not in text]; assert not missing, missing" && docker compose run --rm api pytest -q tests/test_generated_examples.py` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

`File Exists` reflects pre-execution reality. `❌` means the plan intentionally creates that file or test coverage during execution.

---

## Wave 0 Requirements

- [x] Existing pytest, ruff, and Docker-based Python 3.11 verification already cover the repo runtime.
- [x] `tests/test_config_and_registry.py`, `tests/test_analysis_flow.py`, `tests/test_run_lifecycle.py`, `tests/test_monitoring_semantics.py`, `tests/test_api.py`, and `tests/test_cli.py` provide the current seams Phase 6 must preserve.
- [x] Checked generated artifacts and example-based regressions already exist and should remain part of the shipped contract.

---

## Blocking Checkpoints

| Behavior | Plan Checkpoint | Requirement | Why Human Judgment Still Matters | Review Instructions |
|----------|-----------------|-------------|----------------------------------|---------------------|
| Review the partial-recommendation wording before overlay completion is declared truthful | `06-05-CP1` | V2-01 | Automated tests can prove that skipped overlays stay explicit, but they cannot decide whether the resulting memo and `overall_recommendation` still read as honest company-quality-only guidance rather than a fully complete IC call | Confirm the final memo and IC wording clearly distinguish company-quality conclusions from missing or unsupported `security_or_deal_overlay` and `portfolio_fit_positioning` analysis. |
| Review the portfolio-context seam before marking `portfolio_fit_positioning` productionized | `06-05-CP1` | V2-01 | Automated checks can validate payloads and skip behavior, but they cannot judge whether the chosen portfolio input is genuinely book-aware and still narrow enough to preserve the current architecture boundaries | Confirm the implementation uses a narrow reusable context surface, exposes real portfolio/book overlap inputs, and does not widen into bespoke orchestration or an unrestricted tool-calling loop. |

---

## Validation Sign-Off

- [x] All auto tasks have executable `verify` commands, and the only manual judgment point is encoded as a blocking checkpoint in the overlay wave.
- [x] Sampling continuity: every wave ends with an executable full-suite gate.
- [x] Planned Phase 6 test additions are explicitly marked as not yet present in the verification map.
- [x] No watch-mode flags.
- [x] Feedback latency < 180s.
- [x] `nyquist_compliant: true` set in frontmatter.

**Approval:** approved 2026-03-13
