# Factor Ontology

## Principles

- Factors belong to exactly one top-level panel.
- Company quality, security or deal overlay, and portfolio fit remain separate.
- Factors are identified by stable IDs so memory namespaces do not break when display language changes.
- Implementation breadth can lag ontology breadth; a factor may be scaffolded before it has active specialist agents.

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

## Scaffolded Panels

The remaining top-level panels are present in `config/panels.yaml` and `config/factors.yaml` with placeholder prompts and disabled placeholder agents. This lets future work extend the graph surface area by adding prompts, agents, and tool bundles instead of changing the core runtime.

