from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ai_investing.domain.models import CompanyProfile, EvidenceRecord


class SourceConnector(ABC):
    @abstractmethod
    def ingest(self, input_dir: Path) -> tuple[CompanyProfile, list[EvidenceRecord]]:
        raise NotImplementedError
