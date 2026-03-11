# Monitoring

## Monitoring Delta

Each rerun compares current active claims and memo sections against the prior active run.

Tracked outputs:

- changed claim IDs
- changed memo sections
- change summary
- thesis drift flags
- alert level

Materiality rules:

- Confidence drift below `0.05` is not material by itself.
- `what_changed_since_last_run` refreshes on every rerun because it is a run log, not a pure thesis section.
- Material section movement is driven by structured claim and verdict changes plus memo posture shifts, not raw text churn.
- `high` alerts are reserved for recommendation, gatekeeper, survivability, or core risk movement.
- `medium` alerts capture meaningful factor drift without recommendation-level change.
- `low` alerts mean the run log refreshed but the core thesis stayed within the prior range.

## v1 Drift Flags

- `weakening_recurrence`
- `governance_risk_increase`
- `concentration_increase`
- `survivability_deterioration`
