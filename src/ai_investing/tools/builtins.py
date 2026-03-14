from __future__ import annotations

from typing import Any

from ai_investing.application.portfolio import build_portfolio_positioning_context
from ai_investing.domain.models import WriteMemoSectionInput
from ai_investing.monitoring import AnalogGraph, ClaimContradictionService
from ai_investing.tools.base import ToolContext


def evidence_search(context: ToolContext, payload: dict[str, Any]) -> dict[str, Any]:
    records = context.repository.list_evidence(
        context.company_id,
        panel_id=payload.get("panel_id"),
        factor_id=payload.get("factor_id"),
    )
    return {
        "records": [record.model_dump(mode="json") for record in records],
        "output_refs": [f"evidence:{record.evidence_id}" for record in records],
    }


def claim_search(context: ToolContext, payload: dict[str, Any]) -> dict[str, Any]:
    claims = context.repository.list_claim_cards(
        context.company_id,
        panel_id=payload.get("panel_id"),
        factor_id=payload.get("factor_id"),
        active_only=bool(payload.get("active_only", True)),
    )
    return {
        "claims": [claim.model_dump(mode="json") for claim in claims],
        "output_refs": [f"claim:{claim.claim_id}" for claim in claims],
    }


def contradiction_finder(context: ToolContext, payload: dict[str, Any]) -> dict[str, Any]:
    monitoring_config = context.settings.get("monitoring", {})
    service = ClaimContradictionService.from_mapping(monitoring_config.get("contradiction", {}))
    claims = context.repository.list_claim_cards(
        context.company_id,
        panel_id=payload.get("panel_id"),
        active_only=True,
    )
    evidence_records = context.repository.list_evidence(
        context.company_id,
        panel_id=payload.get("panel_id"),
    )
    references = service.find_references(
        claims=claims,
        evidence_records=evidence_records,
        factor_ids=payload.get("factor_ids"),
    )
    contradiction_factors = {reference.factor_id for reference in references if reference.factor_id}
    output_refs = sorted(
        {
            f"claim:{claim.claim_id}"
            for claim in claims
            if claim.factor_id in contradiction_factors
        }.union(
            {
                f"evidence:{record.evidence_id}"
                for record in evidence_records
                if contradiction_factors.intersection(record.factor_ids)
            }
        )
    )
    return {
        "contradictions": [reference.rationale for reference in references],
        "references": [reference.model_dump(mode="json") for reference in references],
        "output_refs": output_refs,
    }


def analog_lookup(context: ToolContext, payload: dict[str, Any]) -> dict[str, Any]:
    monitoring_config = context.settings.get("monitoring", {})
    graph = AnalogGraph.from_mapping(monitoring_config.get("analog", {}))
    references = graph.rank_company(
        context.repository,
        context.company_id,
        factor_ids=payload.get("factor_ids"),
        limit=payload.get("limit"),
    )
    return {
        "notes": [reference.rationale for reference in references],
        "references": [reference.model_dump(mode="json") for reference in references],
        "output_refs": [
            f"company:{reference.company_id}"
            for reference in references
            if reference.company_id is not None
        ],
    }


def portfolio_context_summary(context: ToolContext, payload: dict[str, Any]) -> dict[str, Any]:
    company_id = str(payload.get("company_id") or context.company_id)
    summary = build_portfolio_positioning_context(
        context.repository,
        company_id=company_id,
    )
    if summary is None:
        return {"portfolio_context": None, "output_refs": []}
    return {
        "portfolio_context": summary,
        "output_refs": [
            f"company:{item['company_id']}"
            for item in summary.get("peer_changes", [])
            if item.get("company_id")
        ],
    }


def memo_section_writer(context: ToolContext, payload: dict[str, Any]) -> dict[str, Any]:
    section_input = WriteMemoSectionInput.model_validate(payload)
    return {
        "section": section_input.model_dump(mode="json"),
        "output_refs": [f"memo_section:{section_input.section_id}"],
    }


def public_doc_fetch(context: ToolContext, payload: dict[str, Any]) -> dict[str, Any]:
    return evidence_search(context, payload)


def private_doc_fetch(context: ToolContext, payload: dict[str, Any]) -> dict[str, Any]:
    return evidence_search(context, payload)


def passthrough_stub(_context: ToolContext, payload: dict[str, Any]) -> dict[str, Any]:
    return {"status": "stub", "payload": payload}
