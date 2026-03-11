from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ai_investing.domain.enums import RecordStatus
from ai_investing.domain.models import (
    ClaimCard,
    CompanyProfile,
    CoverageEntry,
    EvidenceRecord,
    GatekeeperVerdict,
    ICMemo,
    MemoSectionUpdate,
    MonitoringDelta,
    PanelVerdict,
    RunRecord,
    ToolInvocationLog,
)
from ai_investing.persistence.tables import (
    ClaimCardRow,
    CompanyProfileRow,
    CoverageEntryRow,
    EvidenceRecordRow,
    MemoRow,
    MemoSectionUpdateRow,
    MonitoringDeltaRow,
    PanelVerdictRow,
    RunRecordRow,
    ToolInvocationLogRow,
)


class Repository:
    def __init__(self, session: Session):
        self.session = session

    def upsert_coverage(self, entry: CoverageEntry) -> CoverageEntry:
        row = self.session.scalar(
            select(CoverageEntryRow).where(CoverageEntryRow.company_id == entry.company_id)
        )
        payload = entry.model_dump(mode="json")
        if row is None:
            row = CoverageEntryRow(
                company_id=entry.company_id,
                company_name=entry.company_name,
                company_type=entry.company_type.value,
                coverage_status=entry.coverage_status.value,
                cadence=entry.cadence.value,
                enabled=entry.enabled,
                next_run_at=entry.next_run_at,
                last_run_at=entry.last_run_at,
                panel_policy=entry.panel_policy,
                memo_label_profile=entry.memo_label_profile,
                notes=entry.notes,
                payload=payload,
            )
            self.session.add(row)
        else:
            row.company_name = entry.company_name
            row.company_type = entry.company_type.value
            row.coverage_status = entry.coverage_status.value
            row.cadence = entry.cadence.value
            row.enabled = entry.enabled
            row.next_run_at = entry.next_run_at
            row.last_run_at = entry.last_run_at
            row.panel_policy = entry.panel_policy
            row.memo_label_profile = entry.memo_label_profile
            row.notes = entry.notes
            row.payload = payload
        return entry

    def list_coverage(
        self, *, enabled_only: bool = False, due_only: bool = False, now: datetime | None = None
    ) -> list[CoverageEntry]:
        stmt = select(CoverageEntryRow)
        if enabled_only:
            stmt = stmt.where(CoverageEntryRow.enabled.is_(True))
        if due_only and now is not None:
            stmt = stmt.where(CoverageEntryRow.next_run_at.is_not(None))
            stmt = stmt.where(CoverageEntryRow.next_run_at <= now)
            stmt = stmt.where(CoverageEntryRow.enabled.is_(True))
        rows = self.session.scalars(stmt.order_by(CoverageEntryRow.company_id)).all()
        return [CoverageEntry.model_validate(row.payload) for row in rows]

    def get_coverage(self, company_id: str) -> CoverageEntry | None:
        row = self.session.scalar(
            select(CoverageEntryRow).where(CoverageEntryRow.company_id == company_id)
        )
        if row is None:
            return None
        return CoverageEntry.model_validate(row.payload)

    def remove_coverage(self, company_id: str) -> None:
        self.session.execute(
            delete(CoverageEntryRow).where(CoverageEntryRow.company_id == company_id)
        )

    def save_company_profile(self, profile: CompanyProfile) -> CompanyProfile:
        row = self.session.scalar(
            select(CompanyProfileRow).where(CompanyProfileRow.company_id == profile.company_id)
        )
        payload = profile.model_dump(mode="json")
        if row is None:
            row = CompanyProfileRow(company_id=profile.company_id, payload=payload)
            self.session.add(row)
        else:
            row.payload = payload
        return profile

    def get_company_profile(self, company_id: str) -> CompanyProfile | None:
        row = self.session.scalar(
            select(CompanyProfileRow).where(CompanyProfileRow.company_id == company_id)
        )
        if row is None:
            return None
        return CompanyProfile.model_validate(row.payload)

    def save_run(self, run: RunRecord) -> RunRecord:
        row = self.session.scalar(select(RunRecordRow).where(RunRecordRow.run_id == run.run_id))
        payload = run.model_dump(mode="json")
        if row is None:
            row = RunRecordRow(
                run_id=run.run_id,
                company_id=run.company_id,
                run_kind=run.run_kind.value,
                status=run.status.value,
                panel_id=run.panel_id,
                started_at=run.started_at,
                completed_at=run.completed_at,
                gate_decision=run.gate_decision.value if run.gate_decision is not None else None,
                awaiting_continue=run.awaiting_continue,
                gated_out=run.gated_out,
                provisional=run.provisional,
                stopped_after_panel=run.stopped_after_panel,
                checkpoint_panel_id=run.checkpoint_panel_id,
                payload=payload,
            )
            self.session.add(row)
        else:
            row.status = run.status.value
            row.panel_id = run.panel_id
            row.completed_at = run.completed_at
            row.gate_decision = run.gate_decision.value if run.gate_decision is not None else None
            row.awaiting_continue = run.awaiting_continue
            row.gated_out = run.gated_out
            row.provisional = run.provisional
            row.stopped_after_panel = run.stopped_after_panel
            row.checkpoint_panel_id = run.checkpoint_panel_id
            row.payload = payload
        return run

    def get_run(self, run_id: str) -> RunRecord | None:
        row = self.session.scalar(select(RunRecordRow).where(RunRecordRow.run_id == run_id))
        if row is None:
            return None
        return RunRecord.model_validate(row.payload)

    def list_runs(self, company_id: str) -> list[RunRecord]:
        rows = self.session.scalars(
            select(RunRecordRow)
            .where(RunRecordRow.company_id == company_id)
            .order_by(RunRecordRow.started_at.desc())
        ).all()
        return [RunRecord.model_validate(row.payload) for row in rows]

    def save_evidence_records(self, records: Sequence[EvidenceRecord]) -> list[EvidenceRecord]:
        for record in records:
            row = self.session.scalar(
                select(EvidenceRecordRow).where(EvidenceRecordRow.evidence_id == record.evidence_id)
            )
            payload = record.model_dump(mode="json")
            if row is None:
                row = EvidenceRecordRow(
                    evidence_id=record.evidence_id,
                    company_id=record.company_id,
                    company_type=record.company_type.value,
                    source_type=record.source_type,
                    title=record.title,
                    namespace=record.namespace,
                    as_of_date=record.as_of_date,
                    payload=payload,
                )
                self.session.add(row)
            else:
                row.payload = payload
        return list(records)

    def list_evidence(
        self, company_id: str, *, panel_id: str | None = None, factor_id: str | None = None
    ) -> list[EvidenceRecord]:
        rows = self.session.scalars(
            select(EvidenceRecordRow)
            .where(EvidenceRecordRow.company_id == company_id)
            .order_by(EvidenceRecordRow.as_of_date.desc())
        ).all()
        records = [EvidenceRecord.model_validate(row.payload) for row in rows]
        if panel_id is not None:
            records = [record for record in records if panel_id in record.panel_ids]
        if factor_id is not None:
            records = [record for record in records if factor_id in record.factor_ids]
        return records

    def save_claim_cards(self, claims: Sequence[ClaimCard]) -> list[ClaimCard]:
        for claim in claims:
            prior_rows = self.session.scalars(
                select(ClaimCardRow).where(
                    ClaimCardRow.company_id == claim.company_id,
                    ClaimCardRow.factor_id == claim.factor_id,
                    ClaimCardRow.agent_id == claim.agent_id,
                    ClaimCardRow.status == RecordStatus.ACTIVE.value,
                )
            ).all()
            for prior_row in prior_rows:
                prior_payload = dict(prior_row.payload)
                prior_payload["status"] = RecordStatus.SUPERSEDED.value
                prior_row.status = RecordStatus.SUPERSEDED.value
                prior_row.payload = prior_payload

            row = ClaimCardRow(
                claim_id=claim.claim_id,
                company_id=claim.company_id,
                run_id=claim.run_id,
                panel_id=claim.panel_id,
                factor_id=claim.factor_id,
                agent_id=claim.agent_id,
                status=claim.status.value,
                namespace=claim.namespace,
                created_at=claim.created_at,
                payload=claim.model_dump(mode="json"),
            )
            self.session.add(row)
        return list(claims)

    def list_claim_cards(
        self,
        company_id: str,
        *,
        run_id: str | None = None,
        panel_id: str | None = None,
        factor_id: str | None = None,
        active_only: bool = False,
    ) -> list[ClaimCard]:
        stmt = select(ClaimCardRow).where(ClaimCardRow.company_id == company_id)
        if run_id is not None:
            stmt = stmt.where(ClaimCardRow.run_id == run_id)
        if panel_id is not None:
            stmt = stmt.where(ClaimCardRow.panel_id == panel_id)
        if factor_id is not None:
            stmt = stmt.where(ClaimCardRow.factor_id == factor_id)
        if active_only:
            stmt = stmt.where(ClaimCardRow.status == RecordStatus.ACTIVE.value)
        rows = self.session.scalars(stmt.order_by(ClaimCardRow.created_at.desc())).all()
        return [ClaimCard.model_validate(row.payload) for row in rows]

    def list_latest_claim_cards_excluding_run(
        self,
        company_id: str,
        *,
        run_id: str,
    ) -> list[ClaimCard]:
        rows = self.session.scalars(
            select(ClaimCardRow)
            .where(ClaimCardRow.company_id == company_id, ClaimCardRow.run_id != run_id)
            .order_by(ClaimCardRow.created_at.desc())
        ).all()
        claims: list[ClaimCard] = []
        seen_keys: set[tuple[str, str]] = set()
        for row in rows:
            claim = ClaimCard.model_validate(row.payload)
            key = (claim.factor_id, claim.agent_id)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            claims.append(claim)
        return claims

    def save_panel_verdict(self, verdict: PanelVerdict) -> PanelVerdict:
        prior_rows = self.session.scalars(
            select(PanelVerdictRow).where(
                PanelVerdictRow.company_id == verdict.company_id,
                PanelVerdictRow.panel_id == verdict.panel_id,
                PanelVerdictRow.status == RecordStatus.ACTIVE.value,
            )
        ).all()
        for prior_row in prior_rows:
            prior_payload = dict(prior_row.payload)
            prior_payload["status"] = RecordStatus.SUPERSEDED.value
            prior_row.status = RecordStatus.SUPERSEDED.value
            prior_row.payload = prior_payload

        row = PanelVerdictRow(
            verdict_id=verdict.verdict_id,
            company_id=verdict.company_id,
            run_id=verdict.run_id,
            panel_id=verdict.panel_id,
            status=verdict.status.value,
            namespace=verdict.namespace,
            created_at=verdict.created_at,
            payload=verdict.model_dump(mode="json"),
        )
        self.session.add(row)
        return verdict

    def list_panel_verdicts(
        self, company_id: str, *, run_id: str | None = None, active_only: bool = False
    ) -> list[PanelVerdict]:
        stmt = select(PanelVerdictRow).where(PanelVerdictRow.company_id == company_id)
        if run_id is not None:
            stmt = stmt.where(PanelVerdictRow.run_id == run_id)
        if active_only:
            stmt = stmt.where(PanelVerdictRow.status == RecordStatus.ACTIVE.value)
        rows = self.session.scalars(stmt.order_by(PanelVerdictRow.created_at.desc())).all()
        return [_deserialize_panel_verdict(row.payload) for row in rows]

    def list_latest_panel_verdicts_excluding_run(
        self,
        company_id: str,
        *,
        run_id: str,
    ) -> list[PanelVerdict]:
        rows = self.session.scalars(
            select(PanelVerdictRow)
            .where(PanelVerdictRow.company_id == company_id, PanelVerdictRow.run_id != run_id)
            .order_by(PanelVerdictRow.created_at.desc())
        ).all()
        verdicts: list[PanelVerdict] = []
        seen_panel_ids: set[str] = set()
        for row in rows:
            verdict = _deserialize_panel_verdict(row.payload)
            if verdict.panel_id in seen_panel_ids:
                continue
            seen_panel_ids.add(verdict.panel_id)
            verdicts.append(verdict)
        return verdicts

    def save_memo(self, memo: ICMemo) -> ICMemo:
        prior_rows = self.session.scalars(
            select(MemoRow).where(
                MemoRow.company_id == memo.company_id, MemoRow.is_active.is_(True)
            )
        ).all()
        for prior_row in prior_rows:
            prior_row.is_active = False
            prior_payload = dict(prior_row.payload)
            prior_payload["is_active"] = False
            prior_row.payload = prior_payload

        row = MemoRow(
            memo_id=memo.memo_id,
            company_id=memo.company_id,
            run_id=memo.run_id,
            is_active=memo.is_active,
            created_at=memo.created_at,
            updated_at=memo.updated_at,
            payload=memo.model_dump(mode="json"),
        )
        self.session.add(row)
        return memo

    def get_current_memo(self, company_id: str) -> ICMemo | None:
        row = self.session.scalar(
            select(MemoRow)
            .where(MemoRow.company_id == company_id, MemoRow.is_active.is_(True))
            .order_by(MemoRow.updated_at.desc())
        )
        if row is None:
            return None
        return ICMemo.model_validate(row.payload)

    def get_latest_memo_excluding_run(self, company_id: str, *, run_id: str) -> ICMemo | None:
        row = self.session.scalar(
            select(MemoRow)
            .where(MemoRow.company_id == company_id, MemoRow.run_id != run_id)
            .order_by(MemoRow.updated_at.desc())
        )
        if row is None:
            return None
        return ICMemo.model_validate(row.payload)

    def get_memo_for_run(self, company_id: str, run_id: str) -> ICMemo | None:
        row = self.session.scalar(
            select(MemoRow)
            .where(MemoRow.company_id == company_id, MemoRow.run_id == run_id)
            .order_by(MemoRow.updated_at.desc())
        )
        if row is None:
            return None
        return ICMemo.model_validate(row.payload)

    def list_memos(self, company_id: str) -> list[ICMemo]:
        rows = self.session.scalars(
            select(MemoRow)
            .where(MemoRow.company_id == company_id)
            .order_by(MemoRow.created_at.desc())
        ).all()
        return [ICMemo.model_validate(row.payload) for row in rows]

    def save_memo_section_update(self, update: MemoSectionUpdate) -> MemoSectionUpdate:
        row = MemoSectionUpdateRow(
            update_id=update.update_id,
            company_id=update.company_id,
            section_id=update.section_id,
            updated_by_run_id=update.updated_by_run_id,
            updated_at=update.updated_at,
            payload=update.model_dump(mode="json"),
        )
        self.session.add(row)
        return update

    def list_memo_section_updates(
        self, company_id: str, *, run_id: str | None = None
    ) -> list[MemoSectionUpdate]:
        stmt = select(MemoSectionUpdateRow).where(MemoSectionUpdateRow.company_id == company_id)
        if run_id is not None:
            stmt = stmt.where(MemoSectionUpdateRow.updated_by_run_id == run_id)
        rows = self.session.scalars(stmt.order_by(MemoSectionUpdateRow.updated_at.desc())).all()
        return [MemoSectionUpdate.model_validate(row.payload) for row in rows]

    def save_monitoring_delta(self, delta: MonitoringDelta) -> MonitoringDelta:
        row = MonitoringDeltaRow(
            delta_id=delta.delta_id,
            company_id=delta.company_id,
            current_run_id=delta.current_run_id,
            created_at=delta.created_at,
            payload=delta.model_dump(mode="json"),
        )
        self.session.add(row)
        return delta

    def get_latest_monitoring_delta(
        self, company_id: str, *, run_id: str | None = None
    ) -> MonitoringDelta | None:
        stmt = select(MonitoringDeltaRow).where(MonitoringDeltaRow.company_id == company_id)
        if run_id is not None:
            stmt = stmt.where(MonitoringDeltaRow.current_run_id == run_id)
        row = self.session.scalar(stmt.order_by(MonitoringDeltaRow.created_at.desc()))
        if row is None:
            return None
        return MonitoringDelta.model_validate(row.payload)

    def save_tool_log(self, log: ToolInvocationLog) -> ToolInvocationLog:
        row = ToolInvocationLogRow(
            log_id=log.log_id,
            run_id=log.run_id,
            agent_id=log.agent_id,
            tool_id=log.tool_id,
            created_at=log.created_at,
            payload=log.model_dump(mode="json"),
        )
        self.session.add(row)
        return log

    def list_tool_logs(self, run_id: str) -> list[ToolInvocationLog]:
        rows = self.session.scalars(
            select(ToolInvocationLogRow)
            .where(ToolInvocationLogRow.run_id == run_id)
            .order_by(ToolInvocationLogRow.created_at.asc())
        ).all()
        return [ToolInvocationLog.model_validate(row.payload) for row in rows]


def _deserialize_panel_verdict(payload: dict) -> PanelVerdict:
    if "gate_decision" in payload:
        return GatekeeperVerdict.model_validate(payload)
    return PanelVerdict.model_validate(payload)
