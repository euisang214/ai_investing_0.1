from __future__ import annotations

from typing import Any

from ai_investing.domain.models import WriteMemoSectionInput
from ai_investing.tools.base import ToolContext


def evidence_search(context: ToolContext, payload: dict[str, Any]) -> dict[str, Any]:
    records = context.repository.list_evidence(
        context.company_id,
        panel_id=payload.get("panel_id"),
        factor_id=payload.get("factor_id"),
    )
    return {"records": [record.model_dump(mode="json") for record in records]}


def claim_search(context: ToolContext, payload: dict[str, Any]) -> dict[str, Any]:
    claims = context.repository.list_claim_cards(
        context.company_id,
        panel_id=payload.get("panel_id"),
        factor_id=payload.get("factor_id"),
        active_only=bool(payload.get("active_only", True)),
    )
    return {"claims": [claim.model_dump(mode="json") for claim in claims]}


def contradiction_finder(context: ToolContext, payload: dict[str, Any]) -> dict[str, Any]:
    claims = context.repository.list_claim_cards(
        context.company_id,
        panel_id=payload.get("panel_id"),
        active_only=True,
    )
    contradictions: list[str] = []
    grouped: dict[str, list[str]] = {}
    for claim in claims:
        grouped.setdefault(claim.factor_id, []).append(claim.claim.lower())
    for factor_id, statements in grouped.items():
        has_positive = any("durable" in statement or "positive" in statement for statement in statements)
        has_negative = any("fragile" in statement or "under pressure" in statement for statement in statements)
        if has_positive and has_negative:
            contradictions.append(f"Conflicting stance detected for {factor_id}.")
    return {"contradictions": contradictions}


def analog_lookup(context: ToolContext, payload: dict[str, Any]) -> dict[str, Any]:
    company_type = str(payload.get("company_type", "both"))
    notes = [
        "Mission-critical workflow software tends to hold pricing better than cyclical tools.",
        "Concentration risk is often the first place thesis drift appears on reruns.",
    ]
    if company_type == "private":
        notes.append("Financing dependency can dominate an otherwise solid operating thesis in private deals.")
    return {"notes": notes}


def memo_section_writer(context: ToolContext, payload: dict[str, Any]) -> dict[str, Any]:
    section_input = WriteMemoSectionInput.model_validate(payload)
    return {"section": section_input.model_dump(mode="json")}


def public_doc_fetch(context: ToolContext, payload: dict[str, Any]) -> dict[str, Any]:
    return evidence_search(context, payload)


def private_doc_fetch(context: ToolContext, payload: dict[str, Any]) -> dict[str, Any]:
    return evidence_search(context, payload)


def passthrough_stub(_context: ToolContext, payload: dict[str, Any]) -> dict[str, Any]:
    return {"status": "stub", "payload": payload}

