from __future__ import annotations

from dataclasses import dataclass

from ai_investing.application.context import AppContext
from ai_investing.domain.enums import CoverageStatus, RefreshJobTrigger
from ai_investing.domain.models import CoverageEntry, RefreshJobRecord, utc_now
from ai_investing.domain.read_models import QueueJobDetail, QueueSummary, ReviewQueueListItem
from ai_investing.persistence.repositories import Repository


@dataclass
class QueueService:
    context: AppContext

    def enqueue_due_coverage(self, *, requested_by: str = "scheduler") -> list[RefreshJobRecord]:
        with self.context.database.session() as session:
            repository = Repository(session)
            entries = repository.list_coverage(enabled_only=True, due_only=True, now=utc_now())
            return self._enqueue_entries(
                repository,
                entries,
                trigger=RefreshJobTrigger.SCHEDULED,
                requested_by=requested_by,
            )

    def enqueue_companies(
        self,
        company_ids: list[str],
        *,
        requested_by: str = "operator",
    ) -> list[RefreshJobRecord]:
        with self.context.database.session() as session:
            repository = Repository(session)
            entries: list[CoverageEntry] = []
            for company_id in company_ids:
                entry = repository.get_coverage(company_id)
                if entry is None:
                    raise KeyError(company_id)
                entries.append(entry)
            return self._enqueue_entries(
                repository,
                entries,
                trigger=RefreshJobTrigger.MANUAL,
                requested_by=requested_by,
            )

    def enqueue_watchlist(self, *, requested_by: str = "operator") -> list[RefreshJobRecord]:
        return self._enqueue_segment(
            CoverageStatus.WATCHLIST,
            trigger=RefreshJobTrigger.BULK_WATCHLIST,
            requested_by=requested_by,
        )

    def enqueue_portfolio(self, *, requested_by: str = "operator") -> list[RefreshJobRecord]:
        return self._enqueue_segment(
            CoverageStatus.PORTFOLIO,
            trigger=RefreshJobTrigger.BULK_PORTFOLIO,
            requested_by=requested_by,
        )

    def get_queue_summary(self) -> QueueSummary:
        with self.context.database.session() as session:
            return Repository(session).get_queue_summary()

    def get_job_detail(self, job_id: str) -> QueueJobDetail:
        with self.context.database.session() as session:
            return Repository(session).get_queue_job_detail(job_id)

    def retry_job(self, job_id: str) -> RefreshJobRecord:
        with self.context.database.session() as session:
            return Repository(session).retry_refresh_job(job_id)

    def cancel_job(self, job_id: str, *, reason: str | None = None) -> RefreshJobRecord:
        with self.context.database.session() as session:
            return Repository(session).cancel_refresh_job(job_id, reason=reason)

    def force_run_job(self, job_id: str) -> RefreshJobRecord:
        with self.context.database.session() as session:
            return Repository(session).force_run_refresh_job(job_id)

    def list_review_queue(self) -> list[ReviewQueueListItem]:
        with self.context.database.session() as session:
            return Repository(session).list_review_queue_items()

    def _enqueue_segment(
        self,
        coverage_status: CoverageStatus,
        *,
        trigger: RefreshJobTrigger,
        requested_by: str,
    ) -> list[RefreshJobRecord]:
        with self.context.database.session() as session:
            repository = Repository(session)
            entries = repository.list_coverage(coverage_statuses=[coverage_status])
            return self._enqueue_entries(
                repository,
                entries,
                trigger=trigger,
                requested_by=requested_by,
            )

    def _enqueue_entries(
        self,
        repository: Repository,
        entries: list[CoverageEntry],
        *,
        trigger: RefreshJobTrigger,
        requested_by: str,
    ) -> list[RefreshJobRecord]:
        jobs: list[RefreshJobRecord] = []
        for entry in entries:
            conflict = repository.get_company_execution_conflict(entry.company_id)
            if isinstance(conflict, RefreshJobRecord):
                jobs.append(conflict)
                continue
            if conflict is not None:
                continue
            jobs.append(
                repository.enqueue_refresh_job(
                    RefreshJobRecord(
                        company_id=entry.company_id,
                        company_name=entry.company_name,
                        coverage_status=entry.coverage_status,
                        trigger=trigger,
                        requested_by=requested_by,
                        scheduled_for=entry.next_run_at,
                    )
                )
            )
        return jobs
