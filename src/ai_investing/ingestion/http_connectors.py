from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

import httpx
from pydantic import BaseModel, ConfigDict, Field

from ai_investing.domain.enums import CompanyType
from ai_investing.domain.models import (
    CompanyProfile,
    EvidenceRecord,
    FactorSignal,
    SourceRef,
    utc_now,
)
from ai_investing.ingestion.base import ConnectorIngestRequest, SourceConnector


class LiveMarketIngestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: str
    company_name: str
    symbol: str
    exchange: str = "NASDAQ"
    company_type: CompanyType = CompanyType.PUBLIC
    description: str
    sector: str | None = None
    headquarters: str | None = None
    tags: list[str] = Field(default_factory=list)
    panel_ids: list[str] = Field(
        default_factory=lambda: ["gatekeepers", "demand_revenue_quality"]
    )
    factor_ids: list[str] = Field(
        default_factory=lambda: ["fad_fashion_risk", "brand_reputation_consideration_set"]
    )


class LiveMarketSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    as_of_date: datetime
    close: float
    change_pct: float
    volume: int
    currency: str = "USD"
    source_url: str


class MarketDataTransport(Protocol):
    def fetch_quote(self, symbol: str) -> LiveMarketSnapshot:
        ...


class YahooChartTransport:
    def __init__(
        self,
        *,
        base_url: str = "https://query1.finance.yahoo.com/v8/finance/chart",
        timeout: float = 10.0,
    ):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def fetch_quote(self, symbol: str) -> LiveMarketSnapshot:
        response = httpx.get(
            f"{self._base_url}/{symbol}",
            params={"interval": "1d", "range": "5d", "includePrePost": "false"},
            headers={"User-Agent": "ai-investing/0.1"},
            follow_redirects=True,
            timeout=self._timeout,
        )
        response.raise_for_status()
        payload = response.json()
        result = payload["chart"]["result"][0]
        timestamps = result["timestamp"]
        quotes = result["indicators"]["quote"][0]
        close_values = quotes.get("close", [])
        volume_values = quotes.get("volume", [])

        latest_index = max(
            index for index, close_value in enumerate(close_values) if close_value is not None
        )
        close = float(close_values[latest_index])
        volume = int(volume_values[latest_index] or 0)
        previous_close = float(result["meta"].get("previousClose") or close)
        change_pct = (
            0.0
            if previous_close == 0
            else ((close - previous_close) / previous_close) * 100
        )
        as_of_date = datetime.fromtimestamp(timestamps[latest_index], tz=UTC)
        return LiveMarketSnapshot(
            symbol=symbol.upper(),
            as_of_date=as_of_date,
            close=close,
            change_pct=change_pct,
            volume=volume,
            currency=str(result["meta"].get("currency") or "USD"),
            source_url=f"https://finance.yahoo.com/quote/{symbol.upper()}",
        )


class PublicMarketLiveConnector(SourceConnector):
    def __init__(
        self,
        *,
        raw_landing_zone: Path,
        request_file: str = "request.json",
        max_staleness_hours: int = 72,
        transport: MarketDataTransport | None = None,
    ):
        self._raw_landing_zone = raw_landing_zone
        self._request_file = request_file
        self._max_staleness_hours = max_staleness_hours
        self._transport = transport or YahooChartTransport()

    def ingest(
        self,
        request: ConnectorIngestRequest,
    ) -> tuple[CompanyProfile, list[EvidenceRecord]]:
        ingest_request = self._load_request(request.input_dir / self._request_file)
        if ingest_request.company_type != CompanyType.PUBLIC:
            raise ValueError("public_market_live_connector only supports public companies.")

        snapshot = self._transport.fetch_quote(ingest_request.symbol)
        landing_dir = self._landing_dir(ingest_request.company_id)
        landing_dir.mkdir(parents=True, exist_ok=True)
        raw_filename = f"{snapshot.symbol.lower()}_quote.json"
        raw_path = landing_dir / raw_filename
        raw_path.write_text(
            json.dumps(
                {
                    "request": ingest_request.model_dump(mode="json"),
                    "snapshot": snapshot.model_dump(mode="json"),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        profile = CompanyProfile(
            company_id=ingest_request.company_id,
            company_name=ingest_request.company_name,
            company_type=ingest_request.company_type,
            description=ingest_request.description,
            sector=ingest_request.sector,
            headquarters=ingest_request.headquarters,
            tags=list(
                dict.fromkeys(
                    [
                        *ingest_request.tags,
                        "live_public",
                        "market",
                        "lightweight_connector",
                    ]
                )
            ),
            namespace=f"company/{ingest_request.company_id}/profile",
        )
        record = EvidenceRecord(
            company_id=ingest_request.company_id,
            company_type=ingest_request.company_type,
            source_type="live_market_snapshot",
            title=f"{ingest_request.symbol.upper()} Live Market Snapshot",
            body=self._body(ingest_request, snapshot),
            source_path=str(raw_path),
            namespace=f"company/{ingest_request.company_id}/evidence",
            panel_ids=ingest_request.panel_ids,
            factor_ids=ingest_request.factor_ids,
            factor_signals=self._factor_signals(snapshot, ingest_request.factor_ids),
            source_refs=[
                SourceRef(
                    label=f"{ingest_request.exchange}:{snapshot.symbol} live quote",
                    url=snapshot.source_url,
                )
            ],
            evidence_quality=0.72,
            staleness_days=max(0, int((utc_now() - snapshot.as_of_date).days)),
            as_of_date=snapshot.as_of_date,
            period="Trailing 5 trading days",
            metadata={
                "connector": "public_market_live_connector",
                "evidence_family": "market",
                "live_connector": True,
                "media_type": "json",
                "symbol": snapshot.symbol,
                "exchange": ingest_request.exchange,
                "quote_close": snapshot.close,
                "quote_change_pct": snapshot.change_pct,
                "quote_volume": snapshot.volume,
                "currency": snapshot.currency,
                "max_staleness_hours": self._max_staleness_hours,
                "staleness_hours": self._staleness_hours(snapshot.as_of_date),
                "staleness_tag": self._staleness_tag(snapshot.as_of_date),
                "raw_basename": raw_filename,
            },
        )
        return profile, [record]

    def _load_request(self, path: Path) -> LiveMarketIngestRequest:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return LiveMarketIngestRequest.model_validate(payload)

    def _landing_dir(self, company_id: str) -> Path:
        timestamp = utc_now().strftime("%Y%m%dT%H%M%SZ")
        return self._raw_landing_zone / company_id / timestamp

    def _body(self, request: LiveMarketIngestRequest, snapshot: LiveMarketSnapshot) -> str:
        return (
            f"{request.company_name} ({snapshot.symbol}) closed at {snapshot.close:.2f} "
            f"{snapshot.currency} on {snapshot.as_of_date.date().isoformat()}, "
            f"moving {snapshot.change_pct:+.2f}% with volume of {snapshot.volume:,}. "
            f"This lightweight live public connector is staleness-tagged and does not "
            f"substitute for richer fixture-backed regulatory, consensus, ownership, "
            f"or dataroom coverage."
        )

    def _factor_signals(
        self,
        snapshot: LiveMarketSnapshot,
        factor_ids: list[str],
    ) -> dict[str, FactorSignal]:
        signals: dict[str, FactorSignal] = {}
        if "brand_reputation_consideration_set" in factor_ids:
            signals["brand_reputation_consideration_set"] = FactorSignal(
                stance="positive" if snapshot.change_pct >= 0 else "mixed",
                summary=(
                    "Recent tape kept the name investable for follow-up work without treating "
                    "price action as a full underwriting substitute."
                ),
                metrics={
                    "close": snapshot.close,
                    "change_pct": round(snapshot.change_pct, 2),
                    "volume": snapshot.volume,
                },
            )
        if "fad_fashion_risk" in factor_ids:
            signals["fad_fashion_risk"] = FactorSignal(
                stance="negative" if abs(snapshot.change_pct) >= 8 else "mixed",
                summary=(
                    "Fast tape moves are tagged as a volatility signal rather than decisive proof "
                    "of durable business quality."
                ),
                metrics={
                    "absolute_change_pct": round(abs(snapshot.change_pct), 2),
                    "volume": snapshot.volume,
                },
            )
        return signals

    def _staleness_hours(self, as_of_date: datetime) -> int:
        return max(0, int((utc_now() - as_of_date).total_seconds() // 3600))

    def _staleness_tag(self, as_of_date: datetime) -> str:
        if self._staleness_hours(as_of_date) <= self._max_staleness_hours:
            return "fresh"
        return "stale"
