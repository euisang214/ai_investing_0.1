from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from ai_investing.application.context import AppContext
from ai_investing.application.services import CoverageService, IngestionService
from ai_investing.domain.enums import Cadence, CompanyType, CoverageStatus
from ai_investing.domain.models import CoverageEntry
from ai_investing.settings import Settings


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def context(tmp_path: Path, repo_root: Path) -> AppContext:
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
