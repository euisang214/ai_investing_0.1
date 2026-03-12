# Management Governance Capital Allocation Scaffold

## Panel Purpose
Assess leadership quality, governance discipline, and capital allocation behavior to judge stewardship durability and avoidable risk.

## Scaffold Status
This panel is scaffold-only. It documents the intended analysis surface for future implementation and is not approved for production execution.

## Output Contract
When implemented, the panel lead must produce a `PanelVerdict` backed by typed evidence, claim cards, and verdict memory records.

## Affected Memo Sections
- `durability_resilience`
- `risk`

## Factor Coverage
- `management_team_per_member`
- `tenure`
- `prior_experience`
- `priorities`
- `ego_self_orientation`
- `planning_execution`
- `criminal_record_reputation`
- `ability_to_hit_projections`
- `employees_unionization_work_culture`
- `org_legal_structure`
- `capital_allocation`
- `incentive_alignment`
- `related_party_red_flags`

## Evidence And Provenance Expectations
- Use sourceable evidence with dates, units, and provenance for biographies, board structure, compensation, capital deployment, and legal history.
- Distinguish polished narrative from demonstrated stewardship by linking management claims to actual outcomes and governance records.
- Flag missing governance evidence explicitly when incentives, related-party exposure, or leadership credibility cannot be grounded.

## Future Implementation Handoff
- Keep the panel id, memo sections, and factor coverage aligned with config before adding runnable agents.
- Reuse the shared debate subgraph when specialists and judge roles are introduced, rather than adding bespoke orchestration.
- Preserve scaffold-only wording until leadership, governance, and capital allocation workflows have repeatable evidence collection and review steps.
