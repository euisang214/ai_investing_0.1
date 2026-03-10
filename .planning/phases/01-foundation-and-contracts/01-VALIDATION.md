---
phase: 01
slug: foundation-and-contracts
status: verified
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-10
updated: 2026-03-10
---

# Phase 01 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest` 8.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `docker compose run --rm api pytest -q tests/test_config_and_registry.py tests/test_repository_semantics.py tests/test_ingestion.py tests/test_api.py tests/test_cli.py tests/test_analysis_flow.py` |
| **Full suite command** | `docker compose run --rm api pytest -q` |
| **Estimated runtime** | ~5-10 seconds including container startup |

---

## Sampling Rate

- **After every task commit:** Run the smallest relevant Docker `pytest` subset and `ruff check .` when Python source changes
- **After every plan wave:** Run `docker compose run --rm api pytest -q`
- **Before `$gsd-verify-work`:** Run `docker compose run --rm api ruff check .`, `docker compose run --rm api mypy src tests`, and `docker compose run --rm api pytest -q`
- **Max feedback latency:** 20 seconds for targeted checks, 30 seconds for full/static runs

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-W0-01 | registry-contracts | 0 | CONF-01 / CONF-03 | unit | `docker compose run --rm api pytest -q tests/test_config_and_registry.py` | ✅ | ✅ green |
| 01-W0-02 | persistence-history | 0 | MEM-01 / MEM-02 | integration | `docker compose run --rm api pytest -q tests/test_repository_semantics.py tests/test_ingestion.py` | ✅ | ✅ green |
| 01-W0-03 | graph-runtime | 0 | ORCH-01 / TOOLS-01 / PROV-01 | integration | `docker compose run --rm api pytest -q tests/test_analysis_flow.py` | ✅ | ✅ green |
| 01-W0-04 | interface-contracts | 0 | API-01 / API-02 | smoke | `docker compose run --rm api pytest -q tests/test_cli.py tests/test_api.py` | ✅ | ✅ green |
| 01-W0-05 | local-ops-path | 0 | OPS-01 | smoke | `docker compose up -d db api && docker compose exec api ai-investing analyze-company ACME` | ✅ | ✅ green |
| 01-W0-06 | static-quality | 0 | Phase 1 baseline | static | `docker compose run --rm api ruff check src tests` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_api.py` — endpoint contract coverage for coverage, company run, memo, delta, and agent management routes
- [x] `tests/test_cli.py` — CLI smoke coverage for init, ingest, coverage, analysis, memo, delta, and agent config commands
- [x] Docker-first boot smoke validation for the documented operator path
- [x] Cross-registry integrity coverage for prompt paths, schema names, and bundle references
- [x] Static quality baseline green in Docker (`ruff`)
- [x] Alembic migration smoke check and legacy-schema bootstrap validation

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Docker-first local workflow from the runbook | OPS-01 | Confirms docs, Compose wiring, and container ergonomics together | Follow `docs/runbook.md` from a clean environment through `analyze-company` |
| Host `uv` workflow if added in this phase | OPS-01 | Python-version and host-environment dependent | Run the documented host setup on Python 3.11+ and verify CLI/API startup |
| CLI readability vs structured output choices | API-01 | Requires human review of operator ergonomics | Run each CLI command and confirm output shape matches the command intent |
| FastAPI envelope/error-shape decisions | API-02 | API contract style is still being established | Exercise error and success responses for representative endpoints and confirm consistency |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** verified 2026-03-10
