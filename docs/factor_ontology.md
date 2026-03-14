# Factor Ontology

## Principles

- factors belong to exactly one top-level panel
- panel ownership stays config-driven
- company quality, expectations, `security_or_deal_overlay`, and `portfolio_fit_positioning` stay analytically separate
- factor ids are stable even when display wording changes
- memo ownership follows panel ownership rather than ad hoc prose conventions

## Implemented Top-Level Panels

The full configured panel surface is now implemented:

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

Policy choice and support posture still determine whether a run reaches a panel and whether that panel executes normally, executes with weak confidence, or is skipped explicitly.

## Panel Families

### Gatekeepers

`gatekeepers` remains the checkpoint family. It owns the early investability and survivability screen:

- `need_to_exist`
- `non_fad_durability`
- `accounting_trustworthiness`
- `balance_sheet_survivability`
- `governance_investability`
- `legal_regulatory_existential_risk`

### Demand And Revenue Quality

`demand_revenue_quality` covers the demand-side quality core:

- `revenue_recurrence_contract_strength`
- `switching_costs`
- `search_costs`
- `customer_habit`
- `fad_fashion_risk`
- `customer_concentration`
- `pricing_power`
- `demand_cyclicality_purchase_deferrability`
- `brand_reputation_consideration_set`

### Internal Company Quality

`supply_product_operations` covers supply-side resilience and product delivery:

- `supply_side_advantage`
- `barriers_to_entry`
- `procurement_supplier_concentration`
- `supplier_fiscal_health`
- `production_distribution_channels`
- `reliability`
- `negotiating_power`
- `input_pricing_availability`
- `product_concentration`
- `innovation`

`management_governance_capital_allocation` covers management execution and governance quality.

`financial_quality_liquidity_economic_model` covers financial quality, liquidity, unit economics, and economic spread.

These families usually support `durability_resilience`, `risk`, and `economic_spread`.

### External Company Quality

`market_structure_growth` covers market shape, share, and growth drivers.

`macro_industry_transmission` covers transmission from macro conditions, policy, and value-chain exposure.

`external_regulatory_geopolitical` covers external regulatory and geopolitical posture.

These families primarily update `growth`, `risk`, and parts of `expectations_variant_view`.

### Expectations

`expectations_catalyst_realization` owns the expectations and catalyst layer.

Its factors stay separate because they depend on consensus, milestone, and realization framing rather than generic quality assessment.

### Overlay Family

`security_or_deal_overlay` covers security-quality or deal-specific overlay work.

`portfolio_fit_positioning` covers book-aware portfolio context and position fit.

They are not synonyms. One can be supported while the other is unsupported, and both can be skipped while the company-quality memo still completes.

## Support Posture By Family

The ontology is broader than a single confidence mode.

- company-quality families may surface `weak_confidence` when evidence exists but does not fully satisfy readiness thresholds
- `expectations_catalyst_realization` requires expectations-specific support and skips when that support is absent
- `security_or_deal_overlay` and `portfolio_fit_positioning` require dedicated context and skip explicitly when that context is unavailable

This keeps the ontology truthful. A missing overlay does not become a hidden null, and a thin company-quality read does not pretend to be high confidence.

## Memo Separation

The panel-to-section contract stays explicit:

- company-quality families influence the core memo view
- expectations work updates `expectations_variant_view` and `realization_path_catalysts`
- `security_or_deal_overlay` updates security-quality or deal-framing output
- `portfolio_fit_positioning` updates portfolio-fit output
- `overall_recommendation` reconciles the executed surface and calls out skipped overlays or weak confidence when relevant

## Operator Interpretation

Read ontology breadth together with policy and support state:

- a panel omitted by policy was not requested
- a panel with `weak_confidence` ran with thin support
- a panel with `unsupported` and a recorded skip was selected but could not run honestly

That distinction is part of the shipped contract, not an implementation detail hidden in tests.
