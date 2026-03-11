from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ai_investing.domain.enums import CompanyType
from ai_investing.domain.models import (
    CompanyProfile,
    EvidenceRecord,
    FactorSignal,
    SourceRef,
    utc_now,
)
from ai_investing.ingestion.base import SourceConnector


class ManifestDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    source_type: str
    title: str
    as_of_date: datetime
    period: str | None = None
    panel_ids: list[str]
    factor_ids: list[str]
    factor_signals: dict[str, FactorSignal]
    source_refs: list[SourceRef]
    metadata: dict[str, Any] = Field(default_factory=dict)


class BundleManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: str
    company_name: str
    company_type: CompanyType
    description: str
    sector: str | None = None
    headquarters: str | None = None
    tags: list[str] = Field(default_factory=list)
    documents: list[ManifestDocument]


class FileBundleConnector(SourceConnector):
    def __init__(self, *, manifest_file: str, raw_landing_zone: Path):
        self._manifest_file = manifest_file
        self._raw_landing_zone = raw_landing_zone

    def ingest(self, input_dir: Path) -> tuple[CompanyProfile, list[EvidenceRecord]]:
        manifest = self._load_manifest(input_dir / self._manifest_file)
        landing_dir = self._landing_dir(manifest.company_id)
        landing_dir.mkdir(parents=True, exist_ok=True)

        records: list[EvidenceRecord] = []
        for document in manifest.documents:
            source_path = input_dir / document.path
            if not source_path.exists():
                raise FileNotFoundError(source_path)
            raw_copy_path = landing_dir / Path(document.path).name
            shutil.copy2(source_path, raw_copy_path)
            body = source_path.read_text(encoding="utf-8")
            quality = self._evidence_quality(document.source_type)
            records.append(
                EvidenceRecord(
                    company_id=manifest.company_id,
                    company_type=manifest.company_type,
                    source_type=document.source_type,
                    title=document.title,
                    body=body,
                    source_path=str(raw_copy_path),
                    namespace=f"company/{manifest.company_id}/evidence",
                    panel_ids=document.panel_ids,
                    factor_ids=document.factor_ids,
                    factor_signals=document.factor_signals,
                    source_refs=document.source_refs,
                    evidence_quality=quality,
                    staleness_days=self._staleness_days(document.as_of_date),
                    as_of_date=document.as_of_date,
                    period=document.period,
                    metadata=document.metadata,
                )
            )

        profile = CompanyProfile(
            company_id=manifest.company_id,
            company_name=manifest.company_name,
            company_type=manifest.company_type,
            description=manifest.description,
            sector=manifest.sector,
            headquarters=manifest.headquarters,
            tags=manifest.tags,
            namespace=f"company/{manifest.company_id}/profile",
        )
        return profile, records

    def _load_manifest(self, path: Path) -> BundleManifest:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return BundleManifest.model_validate(data)

    def _landing_dir(self, company_id: str) -> Path:
        timestamp = utc_now().strftime("%Y%m%dT%H%M%SZ")
        return self._raw_landing_zone / company_id / timestamp

    def _evidence_quality(self, source_type: str) -> float:
        return {
            "regulatory_filing": 0.92,
            "earnings_call": 0.82,
            "investor_presentation": 0.75,
            "board_deck": 0.78,
            "dataroom_financial": 0.85,
            "diligence_note": 0.68,
        }.get(source_type, 0.6)

    def _staleness_days(self, as_of_date: datetime) -> int:
        now = utc_now()
        return max(0, int((now - as_of_date).days))
