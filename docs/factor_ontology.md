# Factor Ontology

## Principles

- Factors belong to exactly one top-level panel.
- Company quality, security or deal overlay, and portfolio fit remain separate.
- Factors are identified by stable IDs so memory namespaces do not break when display language changes.
- Implementation breadth can lag ontology breadth; a factor may be scaffolded before it has active specialist agents.
- Future-facing policies can refer to scaffold-only factor coverage in config before those panels are runnable.

## Implemented v1 Factors

### Gatekeepers

- `need_to_exist`
- `non_fad_durability`
- `accounting_trustworthiness`
- `balance_sheet_survivability`
- `governance_investability`
- `legal_regulatory_existential_risk`

### Demand And Revenue Quality

- `revenue_recurrence_contract_strength`
- `switching_costs`
- `search_costs`
- `customer_habit`
- `fad_fashion_risk`
- `customer_concentration`
- `pricing_power`
- `demand_cyclicality_purchase_deferrability`
- `brand_reputation_consideration_set`

These two panels are the only implemented factor groups in the current runtime.

## Scaffold-Only Factor Groups

The remaining panel ids are present in `config/panels.yaml` and `config/factors.yaml`, but they remain scaffold-only until their agent trees, prompts, and runtime verification are expanded:

- `supply_product_operations`
- `market_structure_growth`
- `macro_industry_transmission`
- `management_governance_capital_allocation`
- `financial_quality_liquidity_economic_model`
- `external_regulatory_geopolitical`
- `expectations_catalyst_realization`
- `security_or_deal_overlay`
- `portfolio_fit_positioning`

This lets the repository keep ontology breadth ahead of implementation breadth without pretending those panels are production-ready. The config can describe the future panel surface and future-facing policies can reference it, while runtime entrypoints still reject scaffold-only panels as not runnable.

## Why The Ontology Is Broader Than The Runtime

The config-driven architecture needs stable factor ownership before every panel is implemented. That is why the repo already carries scaffold-only factor groups in:

- `config/panels.yaml`
- `config/factors.yaml`
- `config/agents.yaml`
- `prompts/`

Keeping those files aligned means a future engineer can productionize one panel at a time without renaming factor ids or rewriting the graph core.

## Short Extension Checklist

When moving a scaffold-only factor group toward production readiness:

1. Confirm panel-to-factor ownership in `config/panels.yaml` and `config/factors.yaml`.
2. Add the correct enabled agent tree in `config/agents.yaml` while preserving the existing panel and factor ids.
3. Replace scaffold prompts in `prompts/` with panel-specific implementation prompts that still target the same contracts.
4. Add or extend tests in `tests/` so factor coverage, prompt assets, and runtime boundaries stay consistent.
5. Preserve the rule that runtime changes happen only when the abstraction truly needs expansion.

For the full worked example and ordered file handoff, see the [panel extension guide](panel_extension_path.md).
