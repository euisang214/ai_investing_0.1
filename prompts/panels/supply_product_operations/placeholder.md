# Supply Product Operations Scaffold

## Panel Purpose
Assess supply-side advantage, operating resilience, and product execution constraints that shape durability and downside risk.

## Scaffold Status
This panel is scaffold-only. It documents the intended analysis surface for future implementation and is not approved for production execution.

## Output Contract
When implemented, the panel lead must produce a `PanelVerdict` backed by typed evidence, claim cards, and verdict memory records.

## Affected Memo Sections
- `durability_resilience`
- `risk`

## Factor Coverage
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

## Evidence And Provenance Expectations
- Use sourceable evidence with dates, units, and provenance for suppliers, channel structure, uptime, fulfillment, and product execution.
- Separate observed operating facts from inferred consequences for margins, resilience, and customer experience.
- Flag missing operational evidence explicitly instead of smoothing over supplier or production blind spots.

## Future Implementation Handoff
- Keep the panel id, memo sections, and factor coverage aligned with config before adding runnable agents.
- Reuse the shared debate subgraph when specialists and judge roles are introduced, rather than adding bespoke orchestration.
- Preserve scaffold-only wording until supply, product, and operations workflows have tool mappings and passing verification coverage.
