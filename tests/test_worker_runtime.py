from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from ai_investing.application.queue import QueueService
from ai_investing.application.services import AnalysisService, CoverageService
from ai_investing.application.worker import WorkerService
from ai_investing.domain.enums import (
    Cadence,
    CompanyType,
    CoverageStatus,
    NotificationCategory,
    RefreshJobStatus,
)
from ai_investing.domain.models import CoverageEntry
from ai_investing.persistence.repositories import Repository
from ai_investing.providers.fake import FakeModelProvider


def _add_coverage(context, company_id: str, company_name: str) -> None:
    CoverageService(context).add_coverage(
        CoverageEntry(
            company_id=company_id,
            company_name=company_name,
            company_type=CompanyType.PUBLIC,
            coverage_status=CoverageStatus.WATCHLIST,
            cadence=Cadence.WEEKLY,
        )
    )


def _force_failed_gatekeeper(monkeypatch: pytest.MonkeyPatch) -> None:
    original_gatekeeper_payload = FakeModelProvider._gatekeeper_payload

    def forced_fail(self, request):
        payload = original_gatekeeper_payload(self, request)
        payload["recommendation"] = "negative"
        payload["gate_decision"] = "fail"
        payload["summary"] = "Gatekeepers failed the company."
        payload["gate_reasons"] = ["Customer concentration remains too high."]
        return payload

    monkeypatch.setattr(FakeModelProvider, "_gatekeeper_payload", forced_fail)


def test_queue_claims_are_multi_worker_safe(context) -> None:
    _add_coverage(context, "ACME", "Acme Cloud")
    _add_coverage(context, "BETA", "Beta Systems")

    queue = QueueService(context)
    queue.enqueue_companies(["ACME", "BETA"])

    worker = WorkerService(context)
    first = worker.claim_jobs(limit=1, worker_id="worker_a")
    second = worker.claim_jobs(limit=2, worker_id="worker_b")

    assert len(first) == 1
    assert len(second) == 1
    assert {first[0].company_id, second[0].company_id} == {"ACME", "BETA"}
    assert first[0].job_id != second[0].job_id


def test_worker_runtime_uses_bounded_parallel_execution(context, monkeypatch) -> None:
    _add_coverage(context, "ACME", "Acme Cloud")
    _add_coverage(context, "BETA", "Beta Systems")
    _add_coverage(context, "GAMMA", "Gamma Software")

    QueueService(context).enqueue_companies(["ACME", "BETA", "GAMMA"])

    lock = threading.Lock()
    active = 0
    max_seen = 0

    def fake_execute_refresh_job(self, job_id: str, *, worker_id: str):
        nonlocal active, max_seen
        with lock:
            active += 1
            max_seen = max(max_seen, active)
        time.sleep(0.05)
        with lock:
            active -= 1
        return {"job_id": job_id, "worker_id": worker_id}

    monkeypatch.setattr(AnalysisService, "execute_refresh_job", fake_execute_refresh_job)

    results = WorkerService(context).run_available_jobs(
        limit=3,
        worker_id="worker_pool",
        max_concurrency=2,
    )

    assert len(results) == 3
    assert max_seen == 2


def test_worker_runtime_persists_running_transition(seeded_acme, monkeypatch) -> None:
    """Worker must call start_refresh_job to transition the job to RUNNING
    before analysis begins, so queue read surfaces can show active work."""
    observed_statuses: list[RefreshJobStatus] = []

    original_execute = AnalysisService.execute_refresh_job

    def capture_running_state(self, job_id: str, *, worker_id: str):
        with self.context.database.session() as session:
            repository = Repository(session)
            job = repository.get_refresh_job(job_id)
            if job is not None:
                observed_statuses.append(job.status)
        return original_execute(self, job_id, worker_id=worker_id)

    monkeypatch.setattr(AnalysisService, "execute_refresh_job", capture_running_state)

    jobs = QueueService(seeded_acme).enqueue_companies(["ACME"])

    results = WorkerService(seeded_acme).run_available_jobs(
        limit=1,
        worker_id="worker_running_test",
        max_concurrency=1,
    )

    assert len(results) == 1

    with seeded_acme.database.session() as session:
        repository = Repository(session)
        job = repository.get_refresh_job(jobs[0].job_id)

    assert job is not None
    assert job.status in {RefreshJobStatus.COMPLETE, RefreshJobStatus.REVIEW_REQUIRED}
    assert job.started_at is not None


def test_worker_runtime_marks_failed_gatekeepers_for_review(seeded_acme, monkeypatch) -> None:
    _force_failed_gatekeeper(monkeypatch)
    queue = QueueService(seeded_acme)
    jobs = queue.enqueue_companies(["ACME"])

    results = WorkerService(seeded_acme).run_available_jobs(
        limit=1,
        worker_id="worker_a",
        max_concurrency=1,
    )

    with seeded_acme.database.session() as session:
        repository = Repository(session)
        job = repository.get_refresh_job(jobs[0].job_id)
        reviews = repository.list_review_queue_items()
        notifications = repository.list_notification_event_items()

    assert results[0]["run"]["status"] == "awaiting_continue"
    assert job is not None
    assert job.status == RefreshJobStatus.REVIEW_REQUIRED
    assert len(reviews) == 1
    assert reviews[0].company_id == "ACME"
    assert NotificationCategory.GATEKEEPER_FAILED in {
        item.category for item in notifications
    }


def test_worker_runtime_emits_material_change_and_daily_digest(
    seeded_acme,
    repo_root: Path,
) -> None:
    initial = AnalysisService(seeded_acme).analyze_company("ACME")

    from ai_investing.application.services import IngestionService

    IngestionService(seeded_acme).ingest_public_data(repo_root / "examples" / "acme_public_rerun")
    jobs = QueueService(seeded_acme).enqueue_companies(["ACME"])
    results = WorkerService(seeded_acme).run_available_jobs(
        limit=1,
        worker_id="worker_b",
        max_concurrency=1,
    )

    with seeded_acme.database.session() as session:
        repository = Repository(session)
        notifications = [
            event
            for event in repository.list_notification_event_items()
            if event.run_id == results[0]["run"]["run_id"]
        ]

    assert initial["run"]["status"] == "complete"
    assert jobs
    assert {event.category for event in notifications} == {
        NotificationCategory.MATERIAL_CHANGE,
        NotificationCategory.DAILY_DIGEST,
    }


def test_worker_runtime_emits_worker_failure_notifications(seeded_acme, monkeypatch) -> None:
    original_generate_structured = FakeModelProvider.generate_structured

    def fail_panel_verdict(self, request, response_model):
        if request.task_type == "panel_verdict":
            raise RuntimeError("panel verdict failure")
        return original_generate_structured(self, request, response_model)

    monkeypatch.setattr(FakeModelProvider, "generate_structured", fail_panel_verdict)

    jobs = QueueService(seeded_acme).enqueue_companies(["ACME"])
    results = WorkerService(seeded_acme).run_available_jobs(
        limit=1,
        worker_id="worker_c",
        max_concurrency=1,
    )

    with seeded_acme.database.session() as session:
        repository = Repository(session)
        job = repository.get_refresh_job(jobs[0].job_id)
        notifications = repository.list_notification_event_items()

    assert "panel verdict failure" in results[0]["error"]
    assert job is not None
    assert job.status == RefreshJobStatus.FAILED
    assert NotificationCategory.WORKER_FAILED in {
        item.category for item in notifications
    }
