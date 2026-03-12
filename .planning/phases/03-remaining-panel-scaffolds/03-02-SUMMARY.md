---
phase: 03-remaining-panel-scaffolds
plan: 02
subsystem: prompting
tags: [yaml, markdown-prompts, pytest, docker-compose, panel-scaffolds]
requires:
  - phase: 03-remaining-panel-scaffolds
    provides: config-backed scaffold panel ids, factor mappings, and placeholder prompt paths from Plan 03-01
provides:
  - panel-specific descriptions for every scaffold-only factor in config/factors.yaml
  - shared scaffold prompt headings across the remaining panel placeholder prompts
  - deterministic prompt asset tests and prompt-strategy guidance tied directly to config
affects: [phase-03, factor-ontology, prompting, test-suite]
tech-stack:
  added: []
  patterns:
    - config-aligned scaffold prompt headings
    - deterministic prompt-to-config contract tests
key-files:
  created:
    - .planning/phases/03-remaining-panel-scaffolds/03-02-SUMMARY.md
    - tests/test_prompt_assets.py
  modified:
    - config/factors.yaml
    - prompts/panels/supply_product_operations/placeholder.md
    - prompts/panels/external_regulatory/placeholder.md
    - prompts/panels/portfolio_fit/placeholder.md
    - docs/prompting_strategy.md
    - docker-compose.yml
key-decisions:
  - "Use one shared Markdown heading contract across scaffold prompts, but bind memo sections and factor coverage directly to panel config."
  - "Keep parent requirement V2-01 open because Plan 03-02 delivers prerequisite slice V2-01B rather than runnable panel implementation."
patterns-established:
  - "Scaffold prompt files mirror panel.memo_section_ids and panel.factor_ids exactly, with deterministic tests enforcing the contract."
  - "Docker verification for prompt strategy docs depends on mounting docs/ into the api service alongside config, prompts, and tests."
requirements-completed: []
duration: 12min
completed: 2026-03-12
---

# Phase 03 Plan 02: Scaffold Prompt Specificity Summary

**Panel-specific scaffold factor ontology, per-panel placeholder prompts, and config-locked prompt asset tests for the remaining non-runnable panels**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-12T11:06:27Z
- **Completed:** 2026-03-12T11:18:44Z
- **Tasks:** 3
- **Files modified:** 13

## Accomplishments

- Replaced every remaining `Placeholder factor` entry with stable, panel-specific ontology text while keeping factor ids unchanged.
- Rewrote all nine scaffold placeholder prompts to share one schema-aware structure with panel-specific memo sections, factor coverage, evidence expectations, and handoff notes.
- Added `tests/test_prompt_assets.py` plus prompt-strategy documentation so scaffold prompts and factor descriptions stay aligned with config over time.

## Task Commits

Each task was committed atomically:

1. **Task 1: Replace generic scaffolded factor descriptions with panel-specific ontology text** - `2695649` (feat)
2. **Task 2: Rewrite every scaffold prompt with a shared but panel-specific structure** - `632a322` (feat)
3. **Task 3: Document and test the scaffold prompt contract** - `8a50862` (chore)

**Plan metadata:** recorded in the subsequent docs/state commit after summary creation

## Files Created/Modified

- `config/factors.yaml` - replaces generic scaffold descriptions with concise panel-specific factor meanings for every non-runnable panel
- `prompts/panels/supply_product_operations/placeholder.md` - establishes the shared scaffold prompt shape for operational panels
- `prompts/panels/market_structure_growth/placeholder.md` - captures market-structure memo impact and growth-factor coverage in the shared scaffold format
- `prompts/panels/macro_industry_transmission/placeholder.md` - defines macro transmission evidence expectations and risk-focused factor coverage
- `prompts/panels/management_governance/placeholder.md` - maps management, governance, and capital-allocation scaffolding to memo risk and durability sections
- `prompts/panels/financial_quality/placeholder.md` - frames financial-quality coverage across economic spread, valuation terms, and risk
- `prompts/panels/external_regulatory/placeholder.md` - records the regulatory and geopolitical scaffold contract used as the representative prompt example
- `prompts/panels/expectations_catalyst_realization/placeholder.md` - defines expectation-setting, falsification, and catalyst scaffolding
- `prompts/panels/security_overlay/placeholder.md` - separates security-specific terms and market structure from company-quality analysis
- `prompts/panels/portfolio_fit/placeholder.md` - ties portfolio interaction, sizing, and exitability scaffolding to the memo contract
- `docs/prompting_strategy.md` - documents required scaffold prompt headings and maintenance rules
- `tests/test_prompt_assets.py` - asserts prompt inventory, headings, config alignment, and non-generic factor descriptions
- `docker-compose.yml` - mounts `docs/` into the `api` service so Docker verification sees prompt-strategy edits

## Decisions Made

- Used one shared set of scaffold prompt headings across the remaining panels so placeholder quality can be tested deterministically without hiding panel specificity in Python.
- Locked affected memo sections and factor coverage directly to `config/panels.yaml` so scaffold prompt drift is treated as a test failure instead of a documentation bug.
- Left parent requirement `V2-01` open because this plan delivers prerequisite slice `V2-01B`, not runnable panel implementation.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Mounted `docs/` into the `api` container so Docker prompt-strategy verification used the edited file**
- **Found during:** Task 3 (Document and test the scaffold prompt contract)
- **Issue:** `docker compose run --rm api python -c ...` saw the stale image copy of `docs/prompting_strategy.md` because the compose service mounted `config`, `prompts`, `src`, and `tests`, but not `docs`.
- **Fix:** Added `./docs:/app/docs` to the `api` service volumes in `docker-compose.yml`, then reran the full Task 3 verification set.
- **Files modified:** `docker-compose.yml`
- **Verification:** `docker compose run --rm api pytest -q tests/test_prompt_assets.py`; `docker compose run --rm api pytest -q tests/test_prompt_assets.py -k factor`; `docker compose run --rm api python -c "from pathlib import Path; text = Path('docs/prompting_strategy.md').read_text(encoding='utf-8'); assert 'memo sections' in text.lower() and 'factor coverage' in text.lower()"`
- **Committed in:** `8a50862` (part of Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** The deviation only repaired the Docker verification environment for prompt-strategy docs. No runtime behavior or panel scope changed.

## Issues Encountered

- Docker verification initially read the stale image copy of `docs/prompting_strategy.md`; mounting `docs/` resolved the mismatch immediately.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 3 now has panel-specific factor meaning and placeholder prompts for the remaining scaffold surface, plus tests that keep prompt headings, memo sections, and factor coverage aligned to config. Later Phase 3 work can focus on runtime-boundary coverage and extension-path documentation without redoing ontology or prompt scaffolding.

## Self-Check: PASSED
