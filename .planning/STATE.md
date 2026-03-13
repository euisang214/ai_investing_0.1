---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_phase: 5
current_phase_name: scheduling and notifications
current_plan: 2
status: in_progress
stopped_at: Completed 05-01-PLAN.md
last_updated: "2026-03-13T15:14:41.479Z"
last_activity: 2026-03-13
progress:
  total_phases: 5
  completed_phases: 4
  total_plans: 20
  completed_plans: 18
  percent: 90
---

# STATE

## Project Reference

See: `.planning/PROJECT.md` (updated 2026-03-08)

**Core value:** Produce a continuously updatable, auditable investment view where factor-level claims, panel verdicts, and memo deltas remain structured and reusable across reruns.
**Current focus:** Phase 5 is underway after Plan 01 established config-driven cadence policies, deterministic schedule semantics, and additive operator schedule controls for later worker and notification work.

## Execution Tracking

**Current Phase:** 5
**Current Phase Name:** scheduling and notifications
**Total Phases:** 5
**Current Plan:** 2
**Total Plans in Phase:** 3
**Status:** Phase in progress
**Progress:** [█████████░] 90%
**Last Activity:** 2026-03-13
**Last Activity Description:** Phase 05 Plan 01 completed with config-driven cadence policies, deterministic schedule advancement, additive CLI/API schedule controls, and a green Docker verification gate

## Current Status

- Phase 1 completed on 2026-03-10 with passing lint, tests, and Docker operator smoke validation.
- Core config, persistence, interface, provider/tool, and orchestration contracts are now in place.
- Phase 2 Plan 01 completed on 2026-03-11 with passing Docker-based tests and lint for the checkpoint runtime slice.
- Phase 2 completed on 2026-03-11 with repaired first-completion baseline semantics, deterministic ACME artifacts, and Docker-verified lint/test/example generation passes.
- Phase 3 Plan 01 completed on 2026-03-12 with normalized disabled placeholder leads, explicit scaffold panel factor mappings, and passing registry verification.
- Phase 3 Plan 02 completed on 2026-03-12 with panel-specific factor ontology, scaffold prompt contracts, prompt-asset tests, and Docker-visible prompt strategy docs.
- Phase 3 Plan 03 completed on 2026-03-12 with service, CLI, and API regressions that keep scaffold-only panels and `full_surface` visible in config while blocking execution before partial runs start.
- Phase 3 Plan 04 completed on 2026-03-12 with repo docs that distinguish implemented versus scaffold-only panels and a worked extension guide for future panel productionization.
- Phase 4 Plan 01 completed on 2026-03-13 with backward-compatible connector config expansion, registry-backed ingestion dispatch, explicit connector-id selection, and Docker-verified tests plus lint.
- Phase 4 Plan 02 completed on 2026-03-13 with representative regulatory, market, consensus, ownership, dataroom, and KPI packets, one lightweight live market connector, truthful docs, and Docker-verified tests plus lint.
- Phase 4 Plan 03 completed on 2026-03-13 with config-backed monitoring enrichment, shared contradiction and analog services, richer additive delta details, regenerated examples, and Docker-verified lint plus tests.
- Phase 4 Plan 04 completed on 2026-03-13 with typed monitoring history and portfolio summary read models, additive CLI/API operator surfaces, read-only boundary documentation, and a full Docker-verified regression pass.
- Phase 5 Plan 01 completed on 2026-03-13 with a typed cadence-policy registry, workspace-timezone schedule computation, additive coverage schedule fields, additive CLI/API controls, regenerated example artifacts, and Docker-verified tests plus lint.
- All remaining top-level panels now have config-backed scaffold topology, panel-specific factor descriptions, and placeholder prompt paths that stay aligned to memo-section and factor mappings.
- The first production panels remain `gatekeepers` and `demand_revenue_quality`, while the remaining panels stay visible in config but non-runnable.
- Phase 3 is complete as a scaffold and documentation phase, but parent requirement `V2-01` remains open until the remaining panels are actually productionized.
- Parent requirement `V2-02` is now satisfied by Plans 04-01 and 04-02, which together deliver the connector runtime seam plus the representative adapter expansion.
- Parent requirement `V2-04` is now satisfied by Plans 04-03 and 04-04, which together deliver the richer monitoring slice plus portfolio-level monitoring history and summary read surfaces.
- Parent requirement `V2-03` is now satisfied by Phase 05 Plan 01, which upgrades coverage scheduling from weekly-only branches to config-driven cadence policies.

## Key Risks

- Local host Python is 3.9.6 while the target runtime must be Python 3.11+ for modern LangGraph support.
- Broad domain scope could tempt bespoke orchestration unless config and subgraph boundaries stay disciplined.
- Sample adapters must stay representative without drifting into speculative connector complexity.

## Next Step

- Execute Phase 05 Plan 02 to add the background refresh queue and notification outbox while preserving the schedule contract established in Plan 01.

## Decisions

- [Phase 02]: Persist awaiting_continue, provisional, gate_decision, and checkpoint_panel_id as typed run fields instead of inferring lifecycle from metadata blobs.
- [Phase 02]: Let LangGraph own the gatekeeper pause/resume path through interrupt() and Command(resume=...) using run_id as the durable thread identity.
- [Phase 02]: Keep analyze_company, refresh_company, and run_panel as public entrypoints, but force downstream panel work to resume existing checkpointed runs instead of bypassing gatekeepers.
- [Phase 02]: Keep checkpointed and completed memo projection in one service pipeline, and express posture through section status plus operator-facing content.
- [Phase 02]: Classify rerun deltas from structured claim, verdict, and memo posture changes while always refreshing the what_changed_since_last_run run log.
- [Phase 02]: Expose tool log provenance as returned evidence, claim, and memo section ids, and mirror stale-evidence semantics in the fake provider for deterministic tests.
- [Phase 02]: Generate ACME artifacts through the same AnalysisService entrypoints the app exposes, not a parallel sample runtime.
- [Phase 02]: Enforce reproducibility by driving IDs and timestamps through patchable shared clock/id seams, then lock checked-in files to generator output.
- [Phase 02]: Verify the plan in Docker because the host machine still defaults to Python 3.9 while the repo targets Python 3.11+.
- [Phase 02]: Treat explicit null and empty baseline metadata as intentional no-baseline state during resume.
- [Phase 02]: Recover legacy paused-run baselines from the latest non-current memo, claim, and verdict history instead of the paused run's promoted active state.
- [Phase 02]: Keep same-run placeholder memo sections not_advanced on first completion and reserve stale carry-forward for true reruns.
- [Phase 03]: Make scaffold factor ownership explicit through panel.factor_ids rather than relying on implicit grouping in factors.yaml.
- [Phase 03]: Normalize scaffold-only panels around one disabled lead placeholder instead of adding deeper agent trees in Phase 3.
- [Phase 03]: Leave parent requirement V2-01 open because Plan 03-01 delivers only prerequisite slice V2-01A.
- [Phase 03]: Keep scaffold execution protection in generic panel resolution and add regressions before changing runtime behavior.
- [Phase 03]: Assert the same scaffold-only panel rejection contract across service, CLI, and API while leaving full_surface loadable in config.
- [Phase 03]: Use one shared scaffold prompt heading contract, but bind memo sections and factor coverage directly to panel config.
- [Phase 03]: Keep parent requirement V2-01 open because Plan 03-02 delivers prerequisite slice V2-01B rather than runnable panel implementation.
- [Phase 03]: Keep V2-01 open because Plan 03-04 delivers documentation prerequisite slice V2-01D rather than runnable implementations for the remaining panels.
- [Phase 03]: Document future-facing policies such as full_surface as config-visible but non-runnable until panel implementation work exists, and keep that story consistent across README, architecture, and factor ontology docs.
- [Phase 04]: Keep legacy manifest_file and raw_landing_zone fields valid while normalizing them into connector settings for future adapter growth.
- [Phase 04]: Resolve connector ids through a dedicated registry and optional wrapper parameters instead of branching inside IngestionService.
- [Phase 04]: Keep V2-02 open because Plan 04-01 delivers connector-runtime slice V2-02A rather than the full connector expansion requirement.
- [Phase 04]: Delegate refresh-time monitoring through MonitoringDeltaService and keep RefreshRuntime focused on memo projection and persistence.
- [Phase 04]: Drive drift, contradiction, analog, and concentration behavior from config so monitoring semantics stay editable without runtime rewrites.
- [Phase 04]: Require evidence-backed contradictions before surfacing factor conflicts so skeptical-agent phrasing does not create false positives.
- [Phase 04]: Keep exactly one lightweight live public connector and require every other family to stay fixture-backed in Phase 4.
- [Phase 04]: Treat PDFs and readable spreadsheet exports as first-class evidence while keeping HTML and image artifacts attachment-only by default.
- [Phase 04]: Preserve flattened raw landing zones and resolve duplicate basenames with stable path-derived filenames instead of nested raw directories.
- [Phase 04]: Keep monitoring history and portfolio monitoring as read-only projections instead of widening orchestration or memo-writing behavior.
- [Phase 04]: Organize portfolio monitoring by change type first while keeping portfolio and watchlist names separate in every group.
- [Phase 04]: Allow portfolio_fit_positioning to appear in monitoring output only as memo projection metadata while keeping the panel scaffold-only.
- [Project-wide override 2026-03-13]: Supersede the Phase 02 universal gatekeeper pause rule. Every run still enters `gatekeepers` first, but `pass` and `review` should continue automatically for both initial and scheduled runs; `fail` should stop after `gatekeepers`, enter a review queue, and notify immediately.
- [Project-wide override 2026-03-13]: Keep provisional downstream analysis explicit and operator-only. Automation may never trigger provisional continuation by default.
- [Phase 05]: Keep legacy cadence as a scheduled-vs-manual compatibility field while schedule_policy_id owns real cadence semantics.
- [Phase 05]: Drive first-run and next-run math through one workspace timezone plus per-coverage preferred run time, with legacy weekly entries staying immediately due unless operators choose a richer policy.
- [Phase 05]: Advance next_run_at only for completed or provisional terminal runs, and clear it for schedule-disabled/manual one-offs so due coverage does not repeat forever.

## Performance Metrics

| Plan | Duration | Scope | Files |
|------|----------|-------|-------|
| Phase 02 P01 | 21 min | 3 tasks | 18 files |
| Phase 02 P02 | 14 min | 3 tasks | 21 files |
| Phase 02 P04 | 10min | 3 tasks | 18 files |
| Phase 02 P05 | 11min | 4 tasks | 16 files |
| Phase 03 P01 | 5min | 3 tasks | 6 files |
| Phase 03 P03 | 13min | 2 tasks | 6 files |
| Phase 03 P02 | 12min | 3 tasks | 13 files |
| Phase 03 P04 | 4min | 3 tasks | 7 files |
| Phase 04 P01 | 10min | 3 tasks | 7 files |
| Phase 04 P03 | 12min | 3 tasks | 19 files |
| Phase 04 P02 | 7min | 3 tasks | 32 files |
| Phase 04 P04 | 16min | 3 tasks | 13 files |
| Phase 05 P01 | 12min | 3 tasks | 16 files |

## Session

**Last Date:** 2026-03-13T15:14:41.476Z
**Stopped At:** Completed 05-01-PLAN.md
**Resume File:** None
