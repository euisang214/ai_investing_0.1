# Memory Model

## Structured Stores

The platform persists the following typed records:

- `CompanyProfile`
- `CoverageEntry`
- `EvidenceRecord`
- `ClaimCard`
- `PanelVerdict` / `GatekeeperVerdict`
- `MemoSectionUpdate`
- `ICMemo`
- `MonitoringDelta`
- `ToolInvocationLog`
- `RunRecord`

## Namespace Conventions

- `company/{company_id}/profile`
- `company/{company_id}/evidence`
- `company/{company_id}/claims/{factor_id}`
- `company/{company_id}/debates/{panel_id}`
- `company/{company_id}/verdicts/{panel_id}`
- `company/{company_id}/memos/current`
- `company/{company_id}/memos/history`
- `company/{company_id}/monitoring`
- `company/{company_id}/tool_logs`
- `portfolio/framework_notes`
- `portfolio/analogs`

## History Rules

- Evidence is append-only.
- New claim cards supersede prior active claim cards for the same `company_id + factor_id + agent_id`.
- New panel verdicts supersede prior active verdicts for the same `company_id + panel_id`.
- Memo snapshots are versioned; only one memo is active at a time.
- Memo section updates are logged independently from memo snapshots.

## Memo Projection Rules

- Every run projects the full required memo section set, even when execution pauses after `gatekeepers`.
- Memo sections use explicit posture states: `refreshed`, `stale`, or `not_advanced`.
- `stale` means prior active memo content is carried forward because the current run did not refresh that section.
- `not_advanced` means the section has never been advanced for the company, or this run stopped before any supporting work existed.
- A gatekeeper-only run must say that deeper work has not run yet instead of inserting generic filler.
- A failed gatekeeper override must keep downstream memo language visibly provisional.
