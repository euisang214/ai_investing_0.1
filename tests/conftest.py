from __future__ import annotations

import shutil
from collections import defaultdict
from contextlib import ExitStack
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from ai_investing.application.context import AppContext
from ai_investing.application.services import CoverageService, IngestionService
from ai_investing.domain.enums import Cadence, CompanyType, CoverageStatus
from ai_investing.domain.models import CoverageEntry
from ai_investing.settings import Settings

UTC = getattr(datetime, "UTC", timezone(timedelta(0)))


@dataclass
class DeterministicRuntime:
    current: datetime = datetime(2026, 3, 11, 9, 0, tzinfo=UTC)
    counters: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def utc_now(self) -> datetime:
        now = self.current
        self.current = now + timedelta(minutes=1)
        return now

    def new_id(self, prefix: str) -> str:
        self.counters[prefix] += 1
        return f"{prefix}_{self.counters[prefix]:012d}"

    def install(self) -> ExitStack:
        stack = ExitStack()
        for target in (
            "ai_investing.domain.models.utc_now",
            "ai_investing.application.services.utc_now",
            "ai_investing.ingestion.file_connectors.utc_now",
            "ai_investing.ingestion.http_connectors.utc_now",
        ):
            stack.enter_context(patch(target, side_effect=self.utc_now))
        for target in (
            "ai_investing.domain.models.new_id",
            "ai_investing.application.services.new_id",
        ):
            stack.enter_context(patch(target, side_effect=self.new_id))
        return stack


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def deterministic_runtime() -> DeterministicRuntime:
    runtime = DeterministicRuntime()
    with runtime.install():
        yield runtime


@pytest.fixture
def context(
    tmp_path: Path,
    repo_root: Path,
    deterministic_runtime: DeterministicRuntime,
) -> AppContext:
    config_dir = tmp_path / "config"
    shutil.copytree(repo_root / "config", config_dir)

    source_connectors_path = config_dir / "source_connectors.yaml"
    source_data = yaml.safe_load(source_connectors_path.read_text(encoding="utf-8"))
    for connector in source_data["connectors"]:
        connector["raw_landing_zone"] = str(tmp_path / connector["id"])
    source_connectors_path.write_text(
        yaml.safe_dump(source_data, sort_keys=False),
        encoding="utf-8",
    )

    settings = Settings(
        database_url="sqlite+pysqlite:///:memory:",
        config_dir=config_dir,
        prompts_dir=repo_root / "prompts",
        provider="fake",
    )
    app_context = AppContext.load(settings)
    app_context.database.initialize()
    return app_context


@pytest.fixture
def seeded_acme(context: AppContext, repo_root: Path) -> AppContext:
    IngestionService(context).ingest_public_data(repo_root / "examples" / "acme_public")
    CoverageService(context).add_coverage(
        CoverageEntry(
            company_id="ACME",
            company_name="Acme Cloud",
            company_type=CompanyType.PUBLIC,
            coverage_status=CoverageStatus.WATCHLIST,
            cadence=Cadence.WEEKLY,
        )
    )
    return context
