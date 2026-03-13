# Monitoring

## Purpose

Monitoring compares the current run against the prior active run using structured claims,
verdicts, memo posture, and evidence signals. It exists to answer a narrow operator question:
what actually changed since the last covered read, and why does it matter?

The monitoring layer is intentionally additive. It deepens `MonitoringDelta` without changing
memo section ids, without rewriting the living memo contract, and without invalidating older
persisted rows or checked-in generated examples.

## Runtime Shape

`RefreshRuntime` delegates monitoring work to `src/ai_investing/monitoring/service.py`.
That service:

- compares current and prior active claims with confidence-aware materiality rules
- maps factor drift through config-backed rules in `config/monitoring.yaml`
- surfaces factor contradictions from structured evidence and claim posture
- ranks top analog or base-rate references through `src/ai_investing/monitoring/analog_graph.py`
- emits current-state concentration and dependency signals instead of only worsening flags
- preserves existing alert semantics unless a change is explicitly backed by tests

Builtin monitoring tools share the same underlying services:

- `contradiction_finder` delegates to the contradiction service
- `analog_lookup` delegates to the analog graph

This keeps the tool surface aligned with the refresh runtime instead of letting monitoring
semantics drift into separate heuristics.

## Delta Contract

`MonitoringDelta` still keeps the original top-level fields:

- `changed_claim_ids`
- `changed_sections`
- `change_summary`
- `thesis_drift_flags`
- `alert_level`

Phase 4 adds optional detail fields:

- `trigger_reasons`: structured reasons behind the delta
- `contradiction_references`: top factor-level contradictions with supporting source refs
- `analog_references`: top analog or base-rate references with similarity rationale
- `concentration_signals`: current-state dependency and concentration views
- `panel_change_hints`: panel-level recommendation or confidence movement hints

These fields are optional and defaulted. Old payloads that only contain the original fields
still deserialize cleanly.

## Summary Versus Detail

Operator output stays intentionally balanced:

- `change_summary` is concise and scan-friendly
- structured detail fields explain why the delta moved

Example shape:

```json
{
  "change_summary": "Acme Cloud rerun detected thesis movement. Material sections: economic_spread. Drift flags: concentration_increase. Contradictions: customer_concentration.",
  "trigger_reasons": [
    {
      "category": "drift",
      "summary": "Customer concentration changed enough to refresh the dependency view.",
      "factor_id": "customer_concentration"
    }
  ],
  "contradiction_references": [
    {
      "category": "contradiction",
      "label": "customer concentration",
      "factor_id": "customer_concentration",
      "rationale": "Conflicting evidence persists on customer concentration: signals span negative, positive."
    }
  ]
}
```

The summary should tell the operator whether the thesis changed. The detail fields should tell
the operator what to inspect next.

## Materiality Rules

Materiality still follows the original vertical-slice behavior:

- confidence-only moves below `0.05` are not material on their own
- `what_changed_since_last_run` always refreshes because it is the run log
- recommendation shifts, gatekeeper changes, and core risk movement remain the main high-alert path
- low-confidence-only drift should not become material just because wording changed cosmetically

The config file keeps these thresholds live:

- `delta_thresholds.confidence_materiality`
- `delta_thresholds.high_alert_changed_sections`
- `delta_thresholds.medium_alert_changed_sections`
- `delta_thresholds.high_alert_drift_flags`
- `delta_thresholds.medium_alert_claim_change_count`

## Drift Rules

Drift flag mapping is no longer trapped in hardcoded `if factor_id == ...` branches.
`config/monitoring.yaml` now declares factor-backed drift rules for the current vertical slice:

- `revenue_recurrence_contract_strength -> weakening_recurrence`
- `governance_investability -> governance_risk_increase`
- `customer_concentration -> concentration_increase`
- `balance_sheet_survivability -> survivability_deterioration`

Each rule can also carry related memo sections and a human-readable reason string.

## Contradictions

Meaningful contradictions are surfaced at the factor level even when recommendation or risk does
not move.

The contradiction service prefers structured evidence posture over role-based debate noise:

- a contradiction exists when evidence on the same factor spans positive and negative stances
- `mixed` only counts as contradictory when it coexists with a directional signal
- low-confidence claim text can contribute, but it does not dominate the result

This prevents the skeptical agent role from automatically marking every factor as contradictory.

## Analog And Base-Rate References

The analog graph ranks candidates deterministically from covered companies already present in the
repository. It compares factor overlap, stance alignment, and shared metric keys, then returns the
top `1-2` references.

The output category depends on the candidate:

- `analog` for same-company-type comparisons
- `base_rate` for cross-type reference points

Each reference includes:

- company id and company name
- the most relevant factor id
- a short explanation of similarity
- the closest supporting source ref when one is available

## Current-State Concentration View

Monitoring now reports current-state dependency posture instead of only worsening flags.
Configured views include:

- customer concentration
- financing dependency
- governance concentration

Each view can emit a stable or pressured state plus a filtered metric snapshot. This gives operators
context even when the alert level stays compatible with the prior behavior.

## Compatibility Notes

The richer monitoring surface preserves backward compatibility in three ways:

1. New `MonitoringDelta` fields are optional and defaulted.
2. Empty additive fields are omitted from serialized output unless populated.
3. Generated examples and legacy payloads remain valid inputs for `MonitoringDelta.model_validate`.

## Verification Expectations

The monitoring regression suite should keep catching the following:

- `what_changed_since_last_run` refreshes on every rerun
- low-confidence-only drift stays non-material
- gatekeeper recommendation movement still escalates to `high`
- factor contradictions surface without requiring recommendation movement
- analog or base-rate ranking stays deterministic for the same fixture set
- old delta payloads and checked-in examples still load without manual backfill
