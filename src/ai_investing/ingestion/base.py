from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from ai_investing.config.models import SourceConnectorConfig
from ai_investing.domain.enums import CompanyType
from ai_investing.domain.models import CompanyProfile, EvidenceRecord


@dataclass(frozen=True)
class ConnectorIngestRequest:
    company_type: CompanyType
    input_dir: Path
    connector_id: str | None = None


class SourceConnector(ABC):
    @abstractmethod
    def ingest(self, input_dir: Path) -> tuple[CompanyProfile, list[EvidenceRecord]]:
        raise NotImplementedError


@dataclass(frozen=True)
class ResolvedSourceConnector:
    config: SourceConnectorConfig
    implementation: SourceConnector

    @property
    def id(self) -> str:
        return self.config.id

    def supports_company_type(self, company_type: CompanyType) -> bool:
        return self.config.supports_company_type(company_type.value)

    def ingest(self, request: ConnectorIngestRequest) -> tuple[CompanyProfile, list[EvidenceRecord]]:
        return self.implementation.ingest(request.input_dir)
