from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

from autograde.models import Artifact, EvidenceObject


class BaseExtractor(ABC):
    extractor_id = "base"
    supported_types: set[str] = set()

    @abstractmethod
    def extract(self, artifact: Artifact) -> List[EvidenceObject]:
        raise NotImplementedError

    @staticmethod
    def read_text(path: str) -> str:
        return Path(path).read_text(encoding="utf-8", errors="ignore")
