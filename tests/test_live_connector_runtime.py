from __future__ import annotations

import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from ai_investing.application.context import AppContext
from ai_investing.application.services import IngestionService
from ai_investing.domain.enums import CompanyType
from ai_investing.ingestion.http_connectors import (
    LiveMarketSnapshot,
    PublicMarketLiveConnector,
)
from ai_investing.ingestion.base import ConnectorIngestRequest
from ai_investing.persistence.repositories import Repository
from ai_investing.settings import Settings

UTC = getattr(datetime, "UTC", timezone(timedelta(0)))


class FakeMarketTransport:
    def __init__(self, snapshot: LiveMarketSnapshot):
        self.snapshot = snapshot
        self.symbols: list[str] = []

    def fetch_quote(self, symbol: str) -> LiveMarketSnapshot:
        self.symbols.append(symbol)
        return self.snapshot


def _load_context(repo_root: Path, config_dir: Path) -> AppContext:
    context = AppContext.load(
        Settings(
            database_url="sqlite+pysqlite:///:memory:",
            config_dir=config_dir,
            prompts_dir=repo_root / "prompts",
            provider="fake",
        )
    )
    context.database.initialize()
    return context


def _config_with_landings(repo_root: Path, tmp_path: Path) -> Path:
    config_dir = tmp_path / "config"
    shutil.copytree(repo_root / "config", config_dir)
    source_connectors_path = config_dir / "source_connectors.yaml"
    source_connectors = yaml.safe_load(source_connectors_path.read_text(encoding="utf-8"))
    for connector in source_connectors["connectors"]:
        connector["raw_landing_zone"] = str(tmp_path / connector["id"])
    source_connectors_path.write_text(
        yaml.safe_dump(source_connectors, sort_keys=False),
        encoding="utf-8",
    )
    return config_dir


def _write_request(input_dir: Path) -> None:
    input_dir.mkdir(parents=True, exist_ok=True)
    (input_dir / "request.json").write_text(
        json.dumps(
            {
                "company_id": "ACME",
                "company_name": "Acme Cloud",
                "company_type": "public",
                "symbol": "ACME",
                "exchange": "NASDAQ",
                "description": "Acme Cloud sells workflow automation software.",
                "sector": "Enterprise Software",
                "headquarters": "New York, NY",
                "tags": ["sample", "live"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def test_public_market_live_connector_uses_typed_transport_double(tmp_path: Path) -> None:
    input_dir = tmp_path / "live_request"
    _write_request(input_dir)
    snapshot = LiveMarketSnapshot(
        symbol="ACME",
        as_of_date=datetime(2026, 3, 11, 14, 0, tzinfo=UTC),
        close=142.75,
        change_pct=4.25,
        volume=1823400,
        currency="USD",
        source_url="https://example.com/acme/live-quote",
    )
    transport = FakeMarketTransport(snapshot)
    connector = PublicMarketLiveConnector(
        raw_landing_zone=tmp_path / "raw-live",
        transport=transport,
        max_staleness_hours=72,
    )
    profile, records = connector.ingest(
        ConnectorIngestRequest(
            company_type=CompanyType.PUBLIC,
            input_dir=input_dir,
            connector_id="public_market_live_connector",
        )
    )

    assert profile.company_id == "ACME"
    assert len(records) == 1
    assert transport.symbols == ["ACME"]
    assert records[0].source_type == "live_market_snapshot"
    assert records[0].metadata["staleness_tag"] == "fresh"
    assert Path(records[0].source_path).is_file()


def test_live_connector_runtime_persists_staleness_tagged_market_evidence(
    repo_root: Path,
    tmp_path: Path,
    monkeypatch,
) -> None:
    config_dir = _config_with_landings(repo_root, tmp_path)
    context = _load_context(repo_root, config_dir)
    input_dir = tmp_path / "live_request"
    _write_request(input_dir)
    snapshot = LiveMarketSnapshot(
        symbol="ACME",
        as_of_date=datetime(2026, 3, 11, 14, 0, tzinfo=UTC),
        close=142.75,
        change_pct=4.25,
        volume=1823400,
        currency="USD",
        source_url="https://example.com/acme/live-quote",
    )

    def build_fake_live_connector(config):
        return PublicMarketLiveConnector(
            raw_landing_zone=Path(config.require_setting("raw_landing_zone")),
            transport=FakeMarketTransport(snapshot),
            max_staleness_hours=config.live_refresh.max_staleness_hours or 72,
        )

    monkeypatch.setattr(
        "ai_investing.ingestion.registry._build_mcp_stub_connector",
        build_fake_live_connector,
    )

    profile, evidence_ids = IngestionService(context).ingest_public_data(
        input_dir,
        connector_id="public_market_live_connector",
    )

    assert profile.company_id == "ACME"
    assert len(evidence_ids) == 1

    with context.database.session() as session:
        repository = Repository(session)
        records = repository.list_evidence("ACME")

    assert len(records) == 1
    record = records[0]
    assert record.source_type == "live_market_snapshot"
    assert "lightweight live public connector" in record.body.lower()
    assert record.metadata["live_connector"] is True
    assert record.metadata["evidence_family"] == "market"
    assert record.metadata["staleness_tag"] == "fresh"
    assert record.metadata["quote_change_pct"] == 4.25
    assert record.metadata["quote_volume"] == 1823400
    assert Path(record.source_path).is_file()
