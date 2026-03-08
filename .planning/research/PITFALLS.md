# Pitfalls Research

## Pitfalls

### Hardcoded Cohort Topology

- Warning signs: panel IDs appear in service code outside config-loading or policy selection.
- Prevention: keep runtime selection based on registries, run policies, and factor mappings.
- Address in phase: Phase 1

### Memo Rewrite Churn

- Warning signs: every panel verdict rewrites the whole memo snapshot.
- Prevention: persist section-level updates and reconcile only at the end of the run.
- Address in phase: Phase 2

### Provider-Coupled Business Logic

- Warning signs: claim synthesis or memo logic assumes one vendor schema or SDK.
- Prevention: isolate providers behind a canonical `ModelProvider` interface and fake provider fixtures.
- Address in phase: Phase 1

### Connector Scope Creep

- Warning signs: large effort spent on premium vendor adapters before vertical slice outputs exist.
- Prevention: implement file-based sample connectors and stub MCP adapters first.
- Address in phase: Phase 1

### Mixed Verdict Domains

- Warning signs: portfolio fit, security overlay, and company quality collapse into a single factor score.
- Prevention: preserve separate panels, separate section impacts, and separate memo sections.
- Address in phase: Phase 2
