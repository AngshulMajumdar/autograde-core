from __future__ import annotations

from pathlib import Path
from typing import List

from autograde.extractors.base import BaseExtractor
from autograde.models import Artifact, EvidenceObject, Location


class PlainTextExtractor(BaseExtractor):
    extractor_id = "plain_text_extractor_v1"
    supported_types = {"report", "essay", "text"}

    def extract(self, artifact: Artifact) -> List[EvidenceObject]:
        text = self.read_text(artifact.storage_path)
        chunks = [c.strip() for c in text.split("\n\n") if c.strip()]
        evidence: List[EvidenceObject] = []
        for idx, chunk in enumerate(chunks, start=1):
            preview = chunk[:120].replace("\n", " ")
            evidence.append(
                EvidenceObject(
                    evidence_id=f"{artifact.artifact_id}_txt_{idx}",
                    submission_id=artifact.submission_id,
                    artifact_id=artifact.artifact_id,
                    modality="text",
                    subtype="paragraph",
                    content=chunk,
                    structured_content={"tokens": len(chunk.split())},
                    preview=preview,
                    location=Location(file=Path(artifact.storage_path).name, paragraph=idx),
                    confidence=0.98,
                    extractor_id=self.extractor_id,
                    tags=["text_chunk"],
                )
            )
        return evidence
