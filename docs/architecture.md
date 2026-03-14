# Architecture

## Overview

This repository implements a modular multi-agent investment research platform for public and private company analysis. The shipped runtime composes reusable LangGraph subgraphs, typed persistence, config-driven registries, and memo projection services into one auditable flow that can run narrow or wide panel policies without changing orchestration code.

The runtime stores structured records for:

- evidence
- claim cards
- panel verdicts
- memo sections and memo section updates
- monitoring deltas
- queue, review, and notification events

## Current Runtime Surface

All configured top-level panels are now implemented:

- `gatekeepers`
- `demand_revenue_quality`
- `supply_product_operations`
- `market_structure_growth`
- `macro_industry_transmission`
- `management_governance_capital_allocation`
- `financial_quality_liquidity_economic_model`
- `external_regulatory_geopolitical`
- `expectations_catalyst_realization`
- `security_or_deal_overlay`
- `portfolio_fit_positioning`

Execution breadth is controlled by run policy, not by changing the graph. `weekly_default` remains the narrow operator default, while `internal_company_quality`, `external_company_quality`, `expectations_rollout`, and `full_surface` expose broader configured slices.

## Layered Design

### 1. Configuration Layer

YAML registries define:

- panels and their readiness or support contracts
- factors and panel ownership
- memo sections
- agent topology
- tool bundles
- run policies
- source connectors

This keeps the cohort config-driven. Adding or changing a panel should normally mean config, prompt, and tests changes rather than orchestration rewrites.

### 2. Domain Contract Layer

Pydantic models define the stable typed records passed between ingestion, orchestration, memo logic, and interfaces. That includes `ClaimCard`, `PanelVerdict`, `PanelSupportAssessment`, `SkippedPanelResult`, `MemoSection`, `MemoSectionUpdate`, `ICMemo`, `MonitoringDelta`, and `RunRecord`.

### 3. Persistence Layer

Postgres stores typed records and preserves history with additive status transitions rather than destructive overwrites. Prior beliefs are superseded or rejected, not erased.

### 4. Orchestration Layer

LangGraph composes one shared company refresh runtime from reusable subgraphs:

- `gatekeepers`
- `debate`
- memo update
- monitoring delta
- IC reconciliation

The runtime does not branch into bespoke per-panel graphs for the Phase 6 surface. `gatekeepers` remains the only special checkpoint family; the remaining panels fit the shared debate path.

### 5. Interface Layer

CLI and FastAPI both call the same application services. n8n remains outside the reasoning runtime and uses stable enqueue, ingest, review, and notification endpoints instead of coordinating panel sequencing directly.

## Run Policy Contract

`config/run_policies.yaml` now describes five important surfaces:

- `weekly_default`
- `internal_company_quality`
- `external_company_quality`
- `expectations_rollout`
- `full_surface`

The policy selects the panel set. The support contract then decides, panel by panel, whether the selected panel is:

- runnable with normal confidence
- runnable with `weak_confidence`
- explicitly skipped as unsupported

This separation matters. A panel being productionized means the runtime knows how to run it honestly. It does not mean every run or every default policy must include it.

## Support And Readiness Contract

Each `PanelConfig` carries two related concepts:

- readiness: what the panel normally needs to count as fully supported
- support: what company types it supports and whether weak-confidence fallback exists

The runtime evaluates:

- evidence families available for the panel
- evidence count
- factor coverage ratio
- required context such as `overlay_context` or `portfolio_context`

The result is persisted as `PanelSupportAssessment`.

### Supported

`supported` means the panel met its configured bar and executed normally.

### Weak Confidence

`weak_confidence` means the panel still ran, but the evidence is thinner than the normal readiness threshold. This is mainly allowed for company-quality panels so the runtime can produce a truthful but cautious update instead of hiding panel output.

The memo layer propagates that posture into affected sections. Operators do not need to infer the thin-support condition from raw claim volume.

### Unsupported Skip

`unsupported` means the panel is explicitly skipped and recorded as `SkippedPanelResult`. The run continues and the skipped panel remains inspectable in:

- run metadata
- CLI and API payloads
- generated artifacts
- memo wording for affected sections

This is critical for `security_or_deal_overlay` and `portfolio_fit_positioning`, where missing support must not masquerade as completed analysis.

## Checkpoint And Continuation Policy

Every run still starts with `gatekeepers`.

- `pass` auto-continues
- `review` auto-continues
- `fail` stops into the review queue and can continue only through explicit operator-only provisional action

That checkpoint contract is persisted even when it resolves automatically so the audit trail is stable across manual, scheduled, and queued runs.

## Panel Families And Memo Ownership

The analytical split is deliberate and must remain intact:

### Company Quality

- `demand_revenue_quality`
- `supply_product_operations`
- `market_structure_growth`
- `macro_industry_transmission`
- `management_governance_capital_allocation`
- `financial_quality_liquidity_economic_model`
- `external_regulatory_geopolitical`

These panels drive most of `investment_snapshot`, `growth`, `durability_resilience`, `risk`, `economic_spread`, and part of `overall_recommendation`.

### Expectations

- `expectations_catalyst_realization`

This panel owns the expectations and catalyst narrative and should not be collapsed into generic company-quality prose.

### Overlay Family

- `security_or_deal_overlay`
- `portfolio_fit_positioning`

These remain distinct from company quality and from each other. `security_or_deal_overlay` represents security-quality or deal-structure framing. `portfolio_fit_positioning` represents portfolio construction context. Neither should be inferred from the other.

## Overall Recommendation Semantics

The memo layer reconciles `overall_recommendation` honestly:

- if overlays are not selected because a narrower policy ran, the memo calls out that the security or deal overlay and portfolio fit positioning are pending for that rollout
- if `full_surface` is selected but overlays lack support, the memo calls out that they were unsupported for this run
- if both overlay panels run, the recommendation scope is overlay-complete

This keeps company-quality output useful without pretending a skipped overlay silently vanished or that unsupported context aborts the whole run.

## Narrow Overlay Context Seam

Phase 6 did not add a new orchestration family for portfolio-aware reasoning. Instead it added a bounded context seam:

- overlay evidence can satisfy `security_or_deal_overlay`
- a narrow portfolio context summary can satisfy `portfolio_fit_positioning`

That keeps portfolio fit config-driven and inspectable without introducing unrestricted agent access to book data.

## Generated Artifact Contract

`scripts/generate_phase2_examples.py` produces checked artifacts that describe the runtime contract directly:

- initial run
- persisted reread of the same run
- rerun with delta behavior
- explicit `full_surface` overlay-gap run where overlays skip but company-quality analysis completes

These artifacts matter because they pin docs, runtime behavior, and operator expectations to reproducible outputs instead of leaving the Phase 6 story scattered across tests.

## Operational Boundary

Queue submission, workers, review queue handling, and notification dispatch stay outside the memo reasoning core.

- scheduling chooses when to run
- queue services choose which coverage enters execution
- the analysis runtime owns panel execution, memo updates, and deltas
- external automation delivers notifications but does not infer investment conclusions

## Non-Goals That Remain Intact

- no frontend analyst UI
- no bespoke orchestration branch per panel family
- no compliance or entitlement workflow system in v1
- no destructive rewrite of prior memo or verdict history
- no collapse of company quality, expectations, `security_or_deal_overlay`, and `portfolio_fit_positioning` into one blended panel
