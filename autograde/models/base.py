from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional


@dataclass(slots=True)
class Location:
    """Traceable location of extracted evidence in an artifact."""

    file: Optional[str] = None
    page: Optional[int] = None
    paragraph: Optional[int] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    cell_index: Optional[int] = None
    region: Optional[str] = None


@dataclass(slots=True)
class EvidenceLink:
    """Typed link between evidence objects."""

    type: str
    target: str


@dataclass(slots=True)
class Artifact:
    artifact_id: str
    submission_id: str
    file_name: str
    artifact_type: str
    mime_type: str
    storage_path: str
    checksum: str
    size_bytes: int
    page_count: Optional[int] = None
    artifact_metadata: Dict[str, Any] = field(default_factory=dict)
    parse_status: str = "pending"


@dataclass(slots=True)
class EvidenceObject:
    evidence_id: str
    submission_id: str
    artifact_id: str
    modality: str
    subtype: str
    content: Optional[str]
    structured_content: Dict[str, Any] = field(default_factory=dict)
    preview: Optional[str] = None
    location: Location = field(default_factory=Location)
    confidence: float = 1.0
    extractor_id: str = ""
    tags: List[str] = field(default_factory=list)
    links: List[EvidenceLink] = field(default_factory=list)
    embedding_ref: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class SubmissionManifest:
    submission_id: str
    artifact_inventory: Dict[str, int] = field(default_factory=dict)
    evidence_inventory: Dict[str, int] = field(default_factory=dict)
    missing_required_artifacts: List[str] = field(default_factory=list)
    unsupported_artifacts: List[str] = field(default_factory=list)
    extraction_warnings: List[Dict[str, Any]] = field(default_factory=list)
    integrity_flags: List[Dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class Submission:
    submission_id: str
    assignment_id: str
    student_id: Optional[str]
    submitted_at: Optional[datetime]
    artifacts: List[Artifact] = field(default_factory=list)
    evidence: List[EvidenceObject] = field(default_factory=list)
    submission_metadata: Dict[str, Any] = field(default_factory=dict)
    integrity_status: str = "pending"
    processing_status: Dict[str, str] = field(
        default_factory=lambda: {
            "ingestion": "pending",
            "extraction": "pending",
            "grading": "pending",
        }
    )
    manifest: SubmissionManifest = field(init=False)

    def __post_init__(self) -> None:
        self.manifest = SubmissionManifest(submission_id=self.submission_id)

    def add_artifact(self, artifact: Artifact) -> None:
        self.artifacts.append(artifact)
        self.manifest.artifact_inventory[artifact.artifact_type] = (
            self.manifest.artifact_inventory.get(artifact.artifact_type, 0) + 1
        )

    def add_evidence(self, evidence: EvidenceObject) -> None:
        self.evidence.append(evidence)
        self.manifest.evidence_inventory[evidence.modality] = (
            self.manifest.evidence_inventory.get(evidence.modality, 0) + 1
        )
