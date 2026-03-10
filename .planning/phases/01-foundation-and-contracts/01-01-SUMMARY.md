---
phase: 01-foundation-and-contracts
plan: 01
subsystem: config
tags: [config, prompts, providers, tools]
requires: []
provides:
  - strict registry cross-reference validation for panels, agents, bundles, and policies
  - prompt-path boundary checks plus deterministic provider selection
  - clearer tool bundle and builtin-handler enforcement
affects: [phase-02, orchestration, api, cli]
tech-stack:
  added: []
  patterns:
    - load-time registry validation before runtime startup
    - explicit provider resolution with fail-fast real-provider errors
key-files:
  created: []
  modified:
    - src/ai_investing/config/models.py
    - src/ai_investing/config/loader.py
    - src/ai_investing/prompts/loader.py
    - src/ai_investing/application/context.py
    - src/ai_investing/tools/registry.py
    - tests/test_config_and_registry.py
key-decisions:
  - "Validate prompt references and schema names at registry load time instead of deferring failures into runtime orchestration."
  - "Treat explicit OpenAI or Anthropic provider selection as a fail-fast contract when env vars or optional packages are missing."
  - "Keep tool bundle and builtin-handler validation centralized in the registry/tool boundary."
patterns-established:
  - "Config-first startup: registry YAML is validated as a coherent bundle before AppContext is constructed."
  - "Provider fallback remains fake-by-default for tests, while explicit real-provider requests fail clearly."
requirements-completed: [CONF-01, CONF-02, CONF-03, MEMO-02, TOOLS-01, PROV-01]
duration: recovery-session
completed: 2026-03-10
---

# Phase 01 Plan 01 Summary

**Config and prompt contracts now fail fast, with deterministic provider routing and stricter tool boundary enforcement.**

## Performance

- **Duration:** recovery session
- **Started:** 2026-03-10T00:00:00Z
- **Completed:** 2026-03-10T02:43:47Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- Added cross-registry validation for memo sections, factors, agents, tool bundles, policies, prompt files, and output schemas.
- Hardened prompt loading so paths must remain under `prompts/` and cannot escape the configured prompt root.
- Made provider selection deterministic and explicit, with runtime dependency checks for real providers and clearer tool-registry failures.

## Task Commits

The executor handoff stalled before task-level commits were produced. Recovery execution continued directly in the workspace and verification was completed against the final working tree.

## Files Created/Modified

- `src/ai_investing/config/models.py` - Added explicit config contracts for supported schemas, subgraphs, and policy safety flags.
- `src/ai_investing/config/loader.py` - Centralized registry bundle validation and prompt-path existence checks.
- `src/ai_investing/prompts/loader.py` - Enforced prompt-root resolution rules.
- `src/ai_investing/application/context.py` - Tightened provider ordering, explicit-provider failure paths, and registry reload behavior.
- `src/ai_investing/tools/registry.py` - Added bundle/tool/handler validation and clearer execution-time errors.
- `tests/test_config_and_registry.py` - Locked the new config, provider, prompt, and tool-registry guarantees into tests.

## Decisions Made

- Prompt and schema validation now lives at load time because orchestration should never start from a partially valid registry state.
- Internal runtime-only agent panel IDs (`memo_updates`, `ic`, `monitoring`) remain explicit exceptions rather than hidden implicit behavior.
- Explicit provider overrides do not silently fall back to fake models when the user asked for a real provider.

## Deviations from Plan

- The original `gsd-executor` fan-out stalled, so this plan was recovered manually in the main workspace.
- No scope was added beyond the planned hardening work and the tests needed to prove it.

## Issues Encountered

- The interrupted executor run left partial edits in API and prompt files; those were reviewed, preserved where correct, and finished during recovery execution.

## User Setup Required

None.

## Next Phase Readiness

- Registry, provider, and tool boundaries are now stable enough for later panel expansion and stricter orchestration.
- Phase 02 can rely on loader-time failures instead of duplicating defensive checks deep in runtime code.

---
*Phase: 01-foundation-and-contracts*
*Completed: 2026-03-10*
