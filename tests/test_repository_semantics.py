from __future__ import annotations

from ai_investing.domain.enums import CompanyType
from ai_investing.domain.models import ClaimCard
from ai_investing.persistence.repositories import Repository


def test_memory_write_read_semantics(context) -> None:
    with context.database.session() as session:
        repository = Repository(session)
        first = ClaimCard(
            company_id="ACME",
            company_type=CompanyType.PUBLIC,
            run_id="run_old",
            panel_id="gatekeepers",
            factor_id="need_to_exist",
            agent_id="gatekeeper_advocate",
            claim="Acme appears durable on need to exist.",
            bull_case="Operationally mandatory.",
            bear_case="Could still be replaced over time.",
            confidence=0.7,
            evidence_quality=0.8,
            staleness_assessment="fresh",
            time_horizon="12 months",
            durability_horizon="multi-year",
            what_changed="Initial coverage run.",
            namespace="company/ACME/claims/need_to_exist",
        )
        repository.save_claim_cards([first])

        second = ClaimCard(
            company_id="ACME",
            company_type=CompanyType.PUBLIC,
            run_id="run_new",
            panel_id="gatekeepers",
            factor_id="need_to_exist",
            agent_id="gatekeeper_advocate",
            claim="Acme appears more fragile on need to exist.",
            bull_case="Still embedded.",
            bear_case="Replacement pressure increased.",
            confidence=0.6,
            evidence_quality=0.7,
            staleness_assessment="fresh",
            time_horizon="12 months",
            durability_horizon="multi-year",
            what_changed="Signal mix changed.",
            namespace="company/ACME/claims/need_to_exist",
        )
        repository.save_claim_cards([second])

        active = repository.list_claim_cards("ACME", active_only=True)
        all_claims = repository.list_claim_cards("ACME", active_only=False)
        assert len(active) == 1
        assert active[0].claim_id == second.claim_id
        assert len(all_claims) == 2
        assert any(claim.status.value == "superseded" for claim in all_claims)
