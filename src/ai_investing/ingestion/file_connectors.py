from __future__ import annotations

import hashlib
import json
import re
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
from ai_investing.ingestion.base import ConnectorIngestRequest, SourceConnector

_MEDIA_TYPE_BY_SUFFIX = {
    ".csv": "spreadsheet",
    ".gif": "image",
    ".htm": "html",
    ".html": "html",
    ".jpeg": "image",
    ".jpg": "image",
    ".json": "text",
    ".md": "text",
    ".pdf": "pdf",
    ".png": "image",
    ".svg": "image",
    ".tsv": "spreadsheet",
    ".txt": "text",
    ".xls": "spreadsheet",
    ".xlsx": "spreadsheet",
}


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

    def ingest(
        self,
        request: ConnectorIngestRequest,
    ) -> tuple[CompanyProfile, list[EvidenceRecord]]:
        manifest = self._load_manifest(request.input_dir / self._manifest_file)
        landing_dir = self._landing_dir(manifest.company_id)
        landing_dir.mkdir(parents=True, exist_ok=True)
        raw_filenames = self._stable_raw_filenames(manifest.documents)

        records: list[EvidenceRecord] = []
        for document in manifest.documents:
            source_path = request.input_dir / document.path
            if not source_path.exists():
                raise FileNotFoundError(source_path)

            raw_copy_path = landing_dir / raw_filenames[document.path]
            shutil.copy2(source_path, raw_copy_path)
            body, extraction_metadata = self._extract_body(source_path, document.metadata)
            metadata = {
                **document.metadata,
                **extraction_metadata,
                "raw_basename": raw_copy_path.name,
                "source_artifact_path": document.path,
            }

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
                    evidence_quality=self._evidence_quality(document.source_type),
                    staleness_days=self._staleness_days(document.as_of_date),
                    as_of_date=document.as_of_date,
                    period=document.period,
                    metadata=metadata,
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

    def _stable_raw_filenames(self, documents: list[ManifestDocument]) -> dict[str, str]:
        basename_counts: dict[str, int] = {}
        for document in documents:
            basename = Path(document.path).name
            basename_counts[basename] = basename_counts.get(basename, 0) + 1

        filenames: dict[str, str] = {}
        used: set[str] = set()
        for document in documents:
            relative_path = Path(document.path)
            basename = relative_path.name
            if basename_counts[basename] == 1 and len(relative_path.parts) == 1:
                candidate = basename
            else:
                candidate = "__".join(relative_path.parts)
            if candidate in used:
                suffix = relative_path.suffix
                digest = hashlib.sha256(relative_path.as_posix().encode("utf-8")).hexdigest()[:8]
                stem = candidate[: -len(suffix)] if suffix else candidate
                candidate = f"{stem}__{digest}{suffix}"
            filenames[document.path] = candidate
            used.add(candidate)
        return filenames

    def _extract_body(
        self,
        source_path: Path,
        metadata: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        media_type = self._media_type(source_path, metadata)
        if self._is_attachment_only(media_type, metadata):
            return (
                self._attachment_only_body(source_path.name, media_type),
                {
                    "attachment_only": True,
                    "extracted_text": False,
                    "media_type": media_type,
                },
            )

        if media_type == "spreadsheet":
            body = self._extract_spreadsheet_text(source_path)
        elif media_type == "pdf":
            body = self._extract_pdf_text(source_path)
        else:
            body = self._read_text_file(source_path)

        return (
            body,
            {
                "attachment_only": False,
                "extracted_text": True,
                "media_type": media_type,
            },
        )

    def _media_type(self, source_path: Path, metadata: dict[str, Any]) -> str:
        declared = metadata.get("media_type")
        if isinstance(declared, str) and declared.strip():
            return declared.strip().lower()
        return _MEDIA_TYPE_BY_SUFFIX.get(source_path.suffix.lower(), "text")

    def _is_attachment_only(self, media_type: str, metadata: dict[str, Any]) -> bool:
        handling = metadata.get("handling")
        if isinstance(handling, str) and handling.strip().lower() == "attachment_only":
            return True
        return media_type in {"html", "image"}

    def _attachment_only_body(self, filename: str, media_type: str) -> str:
        return (
            f"Attachment-only {media_type} artifact stored as {filename}. "
            f"Phase 4 preserves the raw file for provenance without extracting full text."
        )

    def _read_text_file(self, source_path: Path) -> str:
        return source_path.read_text(encoding="utf-8").strip()

    def _extract_pdf_text(self, source_path: Path) -> str:
        content = source_path.read_bytes().decode("latin-1", errors="ignore")
        matches = re.findall(r"\(([^()]*)\)", content)
        if matches:
            return "\n".join(match.strip() for match in matches if match.strip())
        return self._normalize_whitespace(content)

    def _extract_spreadsheet_text(self, source_path: Path) -> str:
        if source_path.suffix.lower() in {".csv", ".tsv"}:
            return self._read_text_file(source_path)

        return self._normalize_whitespace(
            source_path.read_bytes().decode("utf-8", errors="ignore")
        )

    def _normalize_whitespace(self, content: str) -> str:
        lines = [" ".join(line.split()) for line in content.splitlines()]
        normalized = "\n".join(line for line in lines if line)
        return normalized.strip()

    def _evidence_quality(self, source_type: str) -> float:
        return {
            "board_deck": 0.78,
            "consensus_snapshot": 0.72,
            "dataroom_financial": 0.85,
            "diligence_note": 0.68,
            "earnings_call": 0.82,
            "event_image": 0.4,
            "event_page": 0.55,
            "investor_presentation": 0.75,
            "kpi_workbook": 0.8,
            "market_commentary": 0.7,
            "market_snapshot": 0.76,
            "ownership_flow": 0.67,
            "ownership_report": 0.74,
            "public_news": 0.62,
            "regulatory_filing": 0.92,
        }.get(source_type, 0.6)

    def _staleness_days(self, as_of_date: datetime) -> int:
        now = utc_now()
        return max(0, int((now - as_of_date).days))
