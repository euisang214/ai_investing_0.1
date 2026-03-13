from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any

from ai_investing.application.context import AppContext
from ai_investing.application.services import AnalysisService
from ai_investing.domain.models import RefreshJobRecord
from ai_investing.persistence.repositories import Repository


@dataclass
class WorkerService:
    context: AppContext

    def claim_jobs(self, *, limit: int, worker_id: str) -> list[RefreshJobRecord]:
        with self.context.database.session() as session:
            return Repository(session).claim_refresh_jobs(limit=limit, worker_id=worker_id)

    def run_available_jobs(
        self,
        *,
        limit: int,
        worker_id: str,
        max_concurrency: int,
    ) -> list[dict[str, Any]]:
        claimed = self.claim_jobs(limit=limit, worker_id=worker_id)
        if not claimed:
            return []

        results: list[dict[str, Any]] = []
        worker_count = max(1, min(max_concurrency, len(claimed)))
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = {
                executor.submit(self._run_job, job.job_id, worker_id): job.job_id for job in claimed
            }
            for future in as_completed(futures):
                job_id = futures[future]
                try:
                    results.append(future.result())
                except Exception as exc:
                    results.append({"job_id": job_id, "error": str(exc)})
        return results

    def run_job(self, job_id: str, *, worker_id: str) -> dict[str, Any]:
        return self._run_job(job_id, worker_id)

    def _run_job(self, job_id: str, worker_id: str) -> dict[str, Any]:
        return AnalysisService(self.context).execute_refresh_job(job_id, worker_id=worker_id)
