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

