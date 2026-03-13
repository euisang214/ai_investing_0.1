from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ai_investing.domain.enums import (
    CoverageStatus,
    NotificationCategory,
    NotificationStatus,
    RecordStatus,
    RefreshJobStatus,
    ReviewStatus,
    RunStatus,
)
from ai_investing.domain.models import (
    ClaimCard,
    CompanyProfile,
    CoverageEntry,
    EvidenceRecord,
    GatekeeperVerdict,
    ICMemo,
    MemoSectionUpdate,
    MonitoringDelta,
    NotificationEvent,
    PanelVerdict,
    RefreshJobRecord,
    ReviewQueueEntry,
    RunRecord,
    ToolInvocationLog,
    new_id,
    utc_now,
)
from ai_investing.domain.read_models import (
    NotificationEventListItem,
    QueueJobDetail,
    QueueJobListItem,
    QueueStatusCount,
    QueueSummary,
    ReviewQueueListItem,
)
from ai_investing.persistence.tables import (
    ClaimCardRow,
    CompanyProfileRow,
    CoverageEntryRow,
    EvidenceRecordRow,
    MemoRow,
    MemoSectionUpdateRow,
    MonitoringDeltaRow,
    NotificationEventRow,
    PanelVerdictRow,
    RefreshJobRow,
    ReviewQueueEntryRow,
    RunRecordRow,
    ToolInvocationLogRow,
)

_ACTIVE_JOB_STATUSES = {
    RefreshJobStatus.QUEUED.value,
    RefreshJobStatus.CLAIMED.value,
    RefreshJobStatus.RUNNING.value,
    RefreshJobStatus.REVIEW_REQUIRED.value,
}
_IN_FLIGHT_RUN_STATUSES = {
    RunStatus.PENDING.value,
    RunStatus.RUNNING.value,
    RunStatus.AWAITING_CONTINUE.value,
    RunStatus.GATED_OUT.value,
    RunStatus.STOPPED.value,
}


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
        self,
        *,
        enabled_only: bool = False,
        due_only: bool = False,
        now: datetime | None = None,
        coverage_statuses: Sequence[CoverageStatus] | None = None,
    ) -> list[CoverageEntry]:
        stmt = select(CoverageEntryRow)
        if enabled_only:
            stmt = stmt.where(CoverageEntryRow.enabled.is_(True))
        if due_only and now is not None:
            stmt = stmt.where(CoverageEntryRow.next_run_at.is_not(None))
            stmt = stmt.where(CoverageEntryRow.next_run_at <= now)
            stmt = stmt.where(CoverageEntryRow.enabled.is_(True))
        if coverage_statuses:
            stmt = stmt.where(
                CoverageEntryRow.coverage_status.in_([status.value for status in coverage_statuses])
            )
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

    def get_company_execution_conflict(
        self,
        company_id: str,
    ) -> RefreshJobRecord | RunRecord | None:
        active_job = self.find_active_refresh_job(company_id)
        if active_job is not None:
            return active_job
        row = self.session.scalar(
            select(RunRecordRow)
            .where(
                RunRecordRow.company_id == company_id,
                RunRecordRow.status.in_(_IN_FLIGHT_RUN_STATUSES),
            )
            .order_by(RunRecordRow.started_at.desc())
        )
        if row is None:
            return None
        return RunRecord.model_validate(row.payload)

    def save_refresh_job(self, job: RefreshJobRecord) -> RefreshJobRecord:
        row = self.session.scalar(select(RefreshJobRow).where(RefreshJobRow.job_id == job.job_id))
        payload = job.model_dump(mode="json")
        if row is None:
            row = RefreshJobRow(
                job_id=job.job_id,
                company_id=job.company_id,
                company_name=job.company_name,
                coverage_status=job.coverage_status.value,
                run_kind=job.run_kind.value,
                trigger=job.trigger.value,
                status=job.status.value,
                requested_by=job.requested_by,
                priority=job.priority,
                scheduled_for=job.scheduled_for,
                available_at=job.available_at,
                requested_at=job.requested_at,
                claimed_at=job.claimed_at,
                started_at=job.started_at,
                completed_at=job.completed_at,
                run_id=job.run_id,
                review_entry_id=job.review_entry_id,
                worker_id=job.worker_id,
                claim_token=job.claim_token,
                attempt_count=job.attempt_count,
                max_attempts=job.max_attempts,
                cancellation_reason=job.cancellation_reason,
                failure_reason=job.failure_reason,
                payload=payload,
            )
            self.session.add(row)
        else:
            row.company_name = job.company_name
            row.coverage_status = job.coverage_status.value
            row.run_kind = job.run_kind.value
            row.trigger = job.trigger.value
            row.status = job.status.value
            row.requested_by = job.requested_by
            row.priority = job.priority
            row.scheduled_for = job.scheduled_for
            row.available_at = job.available_at
            row.requested_at = job.requested_at
            row.claimed_at = job.claimed_at
            row.started_at = job.started_at
            row.completed_at = job.completed_at
            row.run_id = job.run_id
            row.review_entry_id = job.review_entry_id
            row.worker_id = job.worker_id
            row.claim_token = job.claim_token
            row.attempt_count = job.attempt_count
            row.max_attempts = job.max_attempts
            row.cancellation_reason = job.cancellation_reason
            row.failure_reason = job.failure_reason
            row.payload = payload
        return job

    def get_refresh_job(self, job_id: str) -> RefreshJobRecord | None:
        row = self.session.scalar(select(RefreshJobRow).where(RefreshJobRow.job_id == job_id))
        if row is None:
            return None
        return RefreshJobRecord.model_validate(row.payload)

    def list_refresh_jobs(
        self,
        *,
        statuses: Sequence[RefreshJobStatus] | None = None,
        company_id: str | None = None,
    ) -> list[RefreshJobRecord]:
        stmt = select(RefreshJobRow)
        if company_id is not None:
            stmt = stmt.where(RefreshJobRow.company_id == company_id)
        if statuses:
            stmt = stmt.where(RefreshJobRow.status.in_([status.value for status in statuses]))
        rows = self.session.scalars(
            stmt.order_by(RefreshJobRow.available_at.asc(), RefreshJobRow.requested_at.asc())
        ).all()
        return [RefreshJobRecord.model_validate(row.payload) for row in rows]

    def find_active_refresh_job(self, company_id: str) -> RefreshJobRecord | None:
        row = self.session.scalar(
            select(RefreshJobRow)
            .where(
                RefreshJobRow.company_id == company_id,
                RefreshJobRow.status.in_(_ACTIVE_JOB_STATUSES),
            )
            .order_by(RefreshJobRow.requested_at.desc())
        )
        if row is None:
            return None
        return RefreshJobRecord.model_validate(row.payload)

    def _has_other_active_refresh_job(self, company_id: str, *, exclude_job_id: str) -> bool:
        row = self.session.scalar(
            select(RefreshJobRow)
            .where(
                RefreshJobRow.company_id == company_id,
                RefreshJobRow.status.in_(_ACTIVE_JOB_STATUSES),
                RefreshJobRow.job_id != exclude_job_id,
            )
            .limit(1)
        )
        return row is not None

    def enqueue_refresh_job(self, job: RefreshJobRecord) -> RefreshJobRecord:
        existing_job = self.find_active_refresh_job(job.company_id)
        if existing_job is not None:
            return existing_job
        conflict = self.get_company_execution_conflict(job.company_id)
        if isinstance(conflict, RunRecord):
            raise ValueError(
                f"Company {job.company_id} already has in-flight run {conflict.run_id}."
            )
        return self.save_refresh_job(job)

    def claim_refresh_jobs(
        self,
        *,
        limit: int,
        worker_id: str,
        now: datetime | None = None,
    ) -> list[RefreshJobRecord]:
        claimed_at = now or utc_now()
        rows = self.session.scalars(
            select(RefreshJobRow)
            .where(
                RefreshJobRow.status == RefreshJobStatus.QUEUED.value,
                RefreshJobRow.available_at <= claimed_at,
            )
            .order_by(RefreshJobRow.priority.asc(), RefreshJobRow.available_at.asc())
        ).all()
        claimed: list[RefreshJobRecord] = []
        company_ids: set[str] = set()
        for row in rows:
            if len(claimed) >= limit:
                break
            if row.company_id in company_ids:
                continue
            if self._has_other_active_refresh_job(row.company_id, exclude_job_id=row.job_id):
                continue
            job = RefreshJobRecord.model_validate(row.payload)
            job.status = RefreshJobStatus.CLAIMED
            job.worker_id = worker_id
            job.claimed_at = claimed_at
            job.claim_token = new_id("claim")
            job.attempt_count += 1
            self.save_refresh_job(job)
            claimed.append(job)
            company_ids.add(job.company_id)
        return claimed

    def start_refresh_job(
        self,
        job_id: str,
        *,
        run_id: str,
        worker_id: str | None = None,
        started_at: datetime | None = None,
    ) -> RefreshJobRecord:
        job = self.get_refresh_job(job_id)
        if job is None:
            raise KeyError(job_id)
        job.status = RefreshJobStatus.RUNNING
        job.run_id = run_id
        job.worker_id = worker_id or job.worker_id
        job.started_at = started_at or utc_now()
        return self.save_refresh_job(job)

    def complete_refresh_job(
        self,
        job_id: str,
        *,
        run_id: str | None = None,
        completed_at: datetime | None = None,
    ) -> RefreshJobRecord:
        job = self.get_refresh_job(job_id)
        if job is None:
            raise KeyError(job_id)
        job.status = RefreshJobStatus.COMPLETE
        job.run_id = run_id or job.run_id
        job.completed_at = completed_at or utc_now()
        return self.save_refresh_job(job)

    def mark_refresh_job_review_required(
        self,
        job_id: str,
        *,
        run_id: str,
        review_entry_id: str,
        completed_at: datetime | None = None,
    ) -> RefreshJobRecord:
        job = self.get_refresh_job(job_id)
        if job is None:
            raise KeyError(job_id)
        job.status = RefreshJobStatus.REVIEW_REQUIRED
        job.run_id = run_id
        job.review_entry_id = review_entry_id
        job.completed_at = completed_at or utc_now()
        return self.save_refresh_job(job)

    def fail_refresh_job(
        self,
        job_id: str,
        *,
        error_message: str,
        run_id: str | None = None,
        completed_at: datetime | None = None,
    ) -> RefreshJobRecord:
        job = self.get_refresh_job(job_id)
        if job is None:
            raise KeyError(job_id)
        job.status = RefreshJobStatus.FAILED
        job.failure_reason = error_message
        job.run_id = run_id or job.run_id
        job.completed_at = completed_at or utc_now()
        return self.save_refresh_job(job)

    def cancel_refresh_job(self, job_id: str, *, reason: str | None = None) -> RefreshJobRecord:
        job = self.get_refresh_job(job_id)
        if job is None:
            raise KeyError(job_id)
        job.status = RefreshJobStatus.CANCELLED
        job.cancellation_reason = reason
        job.completed_at = utc_now()
        return self.save_refresh_job(job)

    def retry_refresh_job(
        self,
        job_id: str,
        *,
        available_at: datetime | None = None,
    ) -> RefreshJobRecord:
        job = self.get_refresh_job(job_id)
        if job is None:
            raise KeyError(job_id)
        job.status = RefreshJobStatus.QUEUED
        job.available_at = available_at or utc_now()
        job.claimed_at = None
        job.started_at = None
        job.completed_at = None
        job.worker_id = None
        job.claim_token = None
        job.failure_reason = None
        job.cancellation_reason = None
        return self.save_refresh_job(job)

    def force_run_refresh_job(self, job_id: str) -> RefreshJobRecord:
        job = self.retry_refresh_job(job_id, available_at=utc_now())
        job.trigger = job.trigger.__class__.FORCE_RUN
        return self.save_refresh_job(job)

    def save_review_queue_entry(self, entry: ReviewQueueEntry) -> ReviewQueueEntry:
        row = self.session.scalar(
            select(ReviewQueueEntryRow).where(ReviewQueueEntryRow.review_id == entry.review_id)
        )
        payload = entry.model_dump(mode="json")
        if row is None:
            row = ReviewQueueEntryRow(
                review_id=entry.review_id,
                company_id=entry.company_id,
                company_name=entry.company_name,
                coverage_status=entry.coverage_status.value,
                run_id=entry.run_id,
                job_id=entry.job_id,
                gate_decision=entry.gate_decision.value,
                checkpoint_panel_id=entry.checkpoint_panel_id,
                status=entry.status.value,
                next_action=entry.next_action.value,
                notification_event_id=entry.notification_event_id,
                created_at=entry.created_at,
                acknowledged_at=entry.acknowledged_at,
                resolved_at=entry.resolved_at,
                payload=payload,
            )
            self.session.add(row)
        else:
            row.company_name = entry.company_name
            row.coverage_status = entry.coverage_status.value
            row.run_id = entry.run_id
            row.job_id = entry.job_id
            row.gate_decision = entry.gate_decision.value
            row.checkpoint_panel_id = entry.checkpoint_panel_id
            row.status = entry.status.value
            row.next_action = entry.next_action.value
            row.notification_event_id = entry.notification_event_id
            row.acknowledged_at = entry.acknowledged_at
            row.resolved_at = entry.resolved_at
            row.payload = payload
        return entry

    def get_review_queue_entry(self, review_id: str) -> ReviewQueueEntry | None:
        row = self.session.scalar(
            select(ReviewQueueEntryRow).where(ReviewQueueEntryRow.review_id == review_id)
        )
        if row is None:
            return None
        return ReviewQueueEntry.model_validate(row.payload)

    def list_review_queue(
        self,
        *,
        statuses: Sequence[ReviewStatus] | None = None,
    ) -> list[ReviewQueueEntry]:
        stmt = select(ReviewQueueEntryRow)
        if statuses:
            stmt = stmt.where(ReviewQueueEntryRow.status.in_([status.value for status in statuses]))
        rows = self.session.scalars(stmt.order_by(ReviewQueueEntryRow.created_at.desc())).all()
        return [ReviewQueueEntry.model_validate(row.payload) for row in rows]

    def acknowledge_review_queue_entry(
        self,
        review_id: str,
        *,
        note: str | None = None,
    ) -> ReviewQueueEntry:
        entry = self.get_review_queue_entry(review_id)
        if entry is None:
            raise KeyError(review_id)
        entry.status = ReviewStatus.ACKNOWLEDGED
        entry.acknowledged_at = utc_now()
        if note is not None:
            entry.resolution_note = note
        return self.save_review_queue_entry(entry)

    def resolve_review_queue_entry(
        self,
        review_id: str,
        *,
        note: str | None = None,
    ) -> ReviewQueueEntry:
        entry = self.get_review_queue_entry(review_id)
        if entry is None:
            raise KeyError(review_id)
        entry.status = ReviewStatus.RESOLVED
        entry.resolved_at = utc_now()
        if note is not None:
            entry.resolution_note = note
        return self.save_review_queue_entry(entry)

    def save_notification_event(self, event: NotificationEvent) -> NotificationEvent:
        row = self.session.scalar(
            select(NotificationEventRow).where(NotificationEventRow.event_id == event.event_id)
        )
        payload = event.model_dump(mode="json")
        coverage_status = event.coverage_status.value if event.coverage_status is not None else None
        if row is None:
            row = NotificationEventRow(
                event_id=event.event_id,
                category=event.category.value,
                status=event.status.value,
                company_id=event.company_id,
                company_name=event.company_name,
                coverage_status=coverage_status,
                run_id=event.run_id,
                job_id=event.job_id,
                review_id=event.review_id,
                channel=event.channel,
                title=event.title,
                claimed_by=event.claimed_by,
                claim_token=event.claim_token,
                claimed_at=event.claimed_at,
                dispatched_at=event.dispatched_at,
                acknowledged_at=event.acknowledged_at,
                delivery_attempts=event.delivery_attempts,
                digest_key=event.digest_key,
                created_at=event.created_at,
                payload=payload,
            )
            self.session.add(row)
        else:
            row.category = event.category.value
            row.status = event.status.value
            row.company_id = event.company_id
            row.company_name = event.company_name
            row.coverage_status = coverage_status
            row.run_id = event.run_id
            row.job_id = event.job_id
            row.review_id = event.review_id
            row.channel = event.channel
            row.title = event.title
            row.claimed_by = event.claimed_by
            row.claim_token = event.claim_token
            row.claimed_at = event.claimed_at
            row.dispatched_at = event.dispatched_at
            row.acknowledged_at = event.acknowledged_at
            row.delivery_attempts = event.delivery_attempts
            row.digest_key = event.digest_key
            row.payload = payload
        return event

    def get_notification_event(self, event_id: str) -> NotificationEvent | None:
        row = self.session.scalar(
            select(NotificationEventRow).where(NotificationEventRow.event_id == event_id)
        )
        if row is None:
            return None
        return NotificationEvent.model_validate(row.payload)

    def list_notification_events(
        self,
        *,
        statuses: Sequence[NotificationStatus] | None = None,
        categories: Sequence[NotificationCategory] | None = None,
        company_id: str | None = None,
    ) -> list[NotificationEvent]:
        stmt = select(NotificationEventRow)
        if company_id is not None:
            stmt = stmt.where(NotificationEventRow.company_id == company_id)
        if statuses:
            stmt = stmt.where(
                NotificationEventRow.status.in_([status.value for status in statuses])
            )
        if categories:
            stmt = stmt.where(
                NotificationEventRow.category.in_([category.value for category in categories])
            )
        rows = self.session.scalars(
            stmt.order_by(NotificationEventRow.created_at.asc())
        ).all()
        return [NotificationEvent.model_validate(row.payload) for row in rows]

    def claim_notification_events(
        self,
        *,
        limit: int,
        consumer_id: str,
        now: datetime | None = None,
    ) -> list[NotificationEvent]:
        claimed_at = now or utc_now()
        rows = self.session.scalars(
            select(NotificationEventRow)
            .where(NotificationEventRow.status == NotificationStatus.PENDING.value)
            .order_by(NotificationEventRow.created_at.asc())
            .limit(limit)
        ).all()
        claimed: list[NotificationEvent] = []
        for row in rows:
            event = NotificationEvent.model_validate(row.payload)
            event.status = NotificationStatus.CLAIMED
            event.claimed_by = consumer_id
            event.claimed_at = claimed_at
            event.claim_token = new_id("claim")
            self.save_notification_event(event)
            claimed.append(event)
        return claimed

    def mark_notification_dispatched(self, event_id: str) -> NotificationEvent:
        event = self.get_notification_event(event_id)
        if event is None:
            raise KeyError(event_id)
        event.status = NotificationStatus.DISPATCHED
        event.dispatched_at = utc_now()
        event.delivery_attempts += 1
        return self.save_notification_event(event)

    def acknowledge_notification_event(self, event_id: str) -> NotificationEvent:
        event = self.get_notification_event(event_id)
        if event is None:
            raise KeyError(event_id)
        event.status = NotificationStatus.ACKNOWLEDGED
        event.acknowledged_at = utc_now()
        return self.save_notification_event(event)

    def mark_notification_failed(self, event_id: str, *, error_message: str) -> NotificationEvent:
        event = self.get_notification_event(event_id)
        if event is None:
            raise KeyError(event_id)
        event.status = NotificationStatus.FAILED
        event.last_error = error_message
        event.delivery_attempts += 1
        return self.save_notification_event(event)

    def get_queue_summary(self) -> QueueSummary:
        jobs = self.list_refresh_jobs()
        by_status = [
            QueueStatusCount(status=status, count=sum(1 for job in jobs if job.status == status))
            for status in RefreshJobStatus
            if any(job.status == status for job in jobs)
        ]
        items = [
            QueueJobListItem(
                job_id=job.job_id,
                company_id=job.company_id,
                company_name=job.company_name,
                coverage_status=job.coverage_status,
                run_kind=job.run_kind,
                trigger=job.trigger,
                status=job.status,
                requested_at=job.requested_at,
                available_at=job.available_at,
                run_id=job.run_id,
                review_entry_id=job.review_entry_id,
                worker_id=job.worker_id,
                attempt_count=job.attempt_count,
            )
            for job in jobs
        ]
        return QueueSummary(
            total_jobs=len(jobs),
            active_company_count=len(
                {
                    job.company_id
                    for job in jobs
                    if job.status
                    in {
                        RefreshJobStatus.QUEUED,
                        RefreshJobStatus.CLAIMED,
                        RefreshJobStatus.RUNNING,
                        RefreshJobStatus.REVIEW_REQUIRED,
                    }
                }
            ),
            queued_count=sum(1 for job in jobs if job.status == RefreshJobStatus.QUEUED),
            by_status=by_status,
            jobs=items,
        )

    def get_queue_job_detail(self, job_id: str) -> QueueJobDetail:
        job = self.get_refresh_job(job_id)
        if job is None:
            raise KeyError(job_id)
        review = (
            self.get_review_queue_entry(job.review_entry_id)
            if job.review_entry_id is not None
            else None
        )
        notifications = self.list_notification_events(company_id=job.company_id)
        run_status = None
        if job.run_id is not None:
            run = self.get_run(job.run_id)
            run_status = run.status if run is not None else None
        return QueueJobDetail(
            job=job,
            review=review,
            notifications=[
                event
                for event in notifications
                if event.job_id == job.job_id or event.run_id == job.run_id
            ],
            run_status=run_status,
        )

    def list_review_queue_items(
        self,
        *,
        statuses: Sequence[ReviewStatus] | None = None,
    ) -> list[ReviewQueueListItem]:
        return [
            ReviewQueueListItem(
                review_id=entry.review_id,
                company_id=entry.company_id,
                company_name=entry.company_name,
                coverage_status=entry.coverage_status,
                run_id=entry.run_id,
                job_id=entry.job_id,
                status=entry.status,
                next_action=entry.next_action,
                created_at=entry.created_at,
                notification_event_id=entry.notification_event_id,
                reason_summary=entry.reason_summary,
            )
            for entry in self.list_review_queue(statuses=statuses)
        ]

    def list_notification_event_items(
        self,
        *,
        statuses: Sequence[NotificationStatus] | None = None,
        categories: Sequence[NotificationCategory] | None = None,
    ) -> list[NotificationEventListItem]:
        return [
            NotificationEventListItem(
                event_id=event.event_id,
                category=event.category,
                status=event.status,
                company_id=event.company_id,
                company_name=event.company_name,
                run_id=event.run_id,
                job_id=event.job_id,
                review_id=event.review_id,
                title=event.title,
                next_action=event.next_action,
                delivery_attempts=event.delivery_attempts,
                created_at=event.created_at,
            )
            for event in self.list_notification_events(statuses=statuses, categories=categories)
        ]

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

    def list_monitoring_deltas(
        self,
        company_id: str,
        *,
        run_id: str | None = None,
        limit: int | None = None,
    ) -> list[MonitoringDelta]:
        stmt = select(MonitoringDeltaRow).where(MonitoringDeltaRow.company_id == company_id)
        if run_id is not None:
            stmt = stmt.where(MonitoringDeltaRow.current_run_id == run_id)
        stmt = stmt.order_by(MonitoringDeltaRow.created_at.desc())
        if limit is not None:
            stmt = stmt.limit(limit)
        rows = self.session.scalars(stmt).all()
        return [MonitoringDelta.model_validate(row.payload) for row in rows]

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
