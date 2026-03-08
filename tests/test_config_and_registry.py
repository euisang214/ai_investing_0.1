from __future__ import annotations

import pytest

from ai_investing.application.services import AgentConfigService
from ai_investing.domain.models import ClaimCard


def test_config_loader_validates_registries(context) -> None:
    panels = {panel.id for panel in context.registries.panels.panels}
    assert "gatekeepers" in panels
    assert "demand_revenue_quality" in panels
    assert "portfolio_fit_positioning" in panels
    assert "balanced" in context.registries.model_profiles.model_profiles
    assert "gatekeeper_research" in {
        bundle.id for bundle in context.registries.tool_bundles.bundles
    }


def test_agent_config_updates_persist_and_reload(context) -> None:
    service = AgentConfigService(context)
    disabled = service.disable_agent("demand_skeptic")
    assert disabled.enabled is False

    reparsed = service.reparent_agent("demand_skeptic", "gatekeeper_advocate")
    assert reparsed.parent_id == "gatekeeper_advocate"

    enabled = service.enable_agent("demand_skeptic")
    assert enabled.enabled is True


def test_claim_card_schema_validation() -> None:
    with pytest.raises(ValueError):
        ClaimCard(
            company_id="ACME",
            company_type="public",
            run_id="run_1",
            panel_id="gatekeepers",
            factor_id="need_to_exist",
            agent_id="gatekeeper_advocate",
            claim="bad",
            bull_case="bad",
            bear_case="bad",
            confidence=1.4,
            evidence_quality=0.4,
            staleness_assessment="fresh",
            time_horizon="12 months",
            durability_horizon="multi-year",
            what_changed="none",
            namespace="company/ACME/claims/need_to_exist",
        )

