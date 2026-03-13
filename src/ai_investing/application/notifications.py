from __future__ import annotations

from dataclasses import dataclass

from ai_investing.application.context import AppContext
from ai_investing.domain.enums import NotificationCategory, NotificationStatus
from ai_investing.domain.models import MonitoringDelta, NotificationEvent
from ai_investing.persistence.repositories import Repository


@dataclass
class NotificationService:
    context: AppContext

    def create_event(self, event: NotificationEvent) -> NotificationEvent:
        with self.context.database.session() as session:
            return Repository(session).save_notification_event(event)

    def list_events(
        self,
        *,
        statuses: list[NotificationStatus] | None = None,
        categories: list[NotificationCategory] | None = None,
    ) -> list[NotificationEvent]:
        with self.context.database.session() as session:
            return Repository(session).list_notification_events(
                statuses=statuses,
                categories=categories,
            )

    def claim_pending_events(
        self,
        *,
        limit: int,
        consumer_id: str,
    ) -> list[NotificationEvent]:
        with self.context.database.session() as session:
            return Repository(session).claim_notification_events(
                limit=limit,
                consumer_id=consumer_id,
            )

    def mark_dispatched(self, event_id: str) -> NotificationEvent:
        with self.context.database.session() as session:
            return Repository(session).mark_notification_dispatched(event_id)

    def acknowledge(self, event_id: str) -> NotificationEvent:
        with self.context.database.session() as session:
            return Repository(session).acknowledge_notification_event(event_id)

    def mark_failed(self, event_id: str, *, error_message: str) -> NotificationEvent:
        with self.context.database.session() as session:
            return Repository(session).mark_notification_failed(
                event_id,
                error_message=error_message,
            )

    def emit_gatekeeper_failed(
        self,
        *,
        company_id: str,
        company_name: str,
        coverage_status,
        run_id: str,
        review_id: str,
        job_id: str | None,
        summary: str,
    ) -> NotificationEvent:
        return self.create_event(
            NotificationEvent(
                category=NotificationCategory.GATEKEEPER_FAILED,
                company_id=company_id,
                company_name=company_name,
                coverage_status=coverage_status,
                run_id=run_id,
                review_id=review_id,
                job_id=job_id,
                title=f"Gatekeeper failed for {company_name}",
                summary=summary,
                next_action="continue_provisional",
            )
        )

    def emit_worker_failed(
        self,
        *,
        company_id: str,
        company_name: str,
        coverage_status,
        run_id: str | None,
        job_id: str | None,
        summary: str,
    ) -> NotificationEvent:
        return self.create_event(
            NotificationEvent(
                category=NotificationCategory.WORKER_FAILED,
                company_id=company_id,
                company_name=company_name,
                coverage_status=coverage_status,
                run_id=run_id,
                job_id=job_id,
                title=f"Worker failed for {company_name}",
                summary=summary,
                next_action="retry_job",
            )
        )

    def emit_material_change(
        self,
        *,
        company_id: str,
        company_name: str,
        coverage_status,
        run_id: str,
        job_id: str | None,
        delta: MonitoringDelta,
    ) -> NotificationEvent:
        return self.create_event(
            NotificationEvent(
                category=NotificationCategory.MATERIAL_CHANGE,
                company_id=company_id,
                company_name=company_name,
                coverage_status=coverage_status,
                run_id=run_id,
                job_id=job_id,
                title=f"Material change for {company_name}",
                summary=delta.change_summary,
                next_action="review_run",
                payload=delta.model_dump(mode="json"),
            )
        )

    def emit_daily_digest_candidate(
        self,
        *,
        company_id: str,
        company_name: str,
        coverage_status,
        run_id: str,
        job_id: str | None,
        delta: MonitoringDelta | None,
    ) -> NotificationEvent:
        summary = (
            delta.change_summary
            if delta is not None
            else "Run completed with no material changes to report."
        )
        return self.create_event(
            NotificationEvent(
                category=NotificationCategory.DAILY_DIGEST,
                company_id=company_id,
                company_name=company_name,
                coverage_status=coverage_status,
                run_id=run_id,
                job_id=job_id,
                title=f"Daily digest candidate for {company_name}",
                summary=summary,
                digest_key=run_id,
            )
        )
