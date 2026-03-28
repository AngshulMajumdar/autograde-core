from __future__ import annotations

import hashlib
import tarfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Dict, Iterable

from autograde.extractors import (
    AudioMetadataExtractor,
    CSVTableExtractor,
    DatasetExtractor,
    DocxTextExtractor,
    ImageMetadataExtractor,
    NotebookExtractor,
    PlainTextExtractor,
    PythonCodeExtractor,
    SlideDeckExtractor,
    VideoMetadataExtractor,
)
from autograde.ingestion.classifier import classify_artifact
from autograde.models import Artifact, Submission


class SubmissionIngestionPipeline:
    def __init__(self) -> None:
        extractors = [
            PlainTextExtractor(),
            DocxTextExtractor(),
            PythonCodeExtractor(),
            NotebookExtractor(),
            CSVTableExtractor(),
            DatasetExtractor(),
            ImageMetadataExtractor(),
            SlideDeckExtractor(),
            AudioMetadataExtractor(),
            VideoMetadataExtractor(),
        ]
        self.extractor_registry: Dict[str, object] = {}
        for extractor in extractors:
            for artifact_type in extractor.supported_types:
                self.extractor_registry[artifact_type] = extractor

    def ingest_submission(self, assignment_id: str, submission_path: str, submission_id: str, student_id: str | None = None) -> Submission:
        root = Path(submission_path)
        self._expand_archives(root)
        submission = Submission(
            submission_id=submission_id,
            assignment_id=assignment_id,
            student_id=student_id,
            submitted_at=datetime.now(UTC),
            submission_metadata={"root": str(root)},
        )
        for file_path in self._discover_files(root):
            artifact_type, mime_type = classify_artifact(file_path)
            checksum = self._checksum(file_path)
            artifact = Artifact(
                artifact_id=f"{submission_id}_{len(submission.artifacts)+1:03d}",
                submission_id=submission_id,
                file_name=file_path.name,
                artifact_type=artifact_type,
                mime_type=mime_type,
                storage_path=str(file_path),
                checksum=checksum,
                size_bytes=file_path.stat().st_size,
                parse_status="pending",
            )
            if artifact_type == "unsupported":
                submission.manifest.unsupported_artifacts.append(file_path.name)
                continue

            submission.add_artifact(artifact)
            extractor = self.extractor_registry.get(artifact_type)
            if extractor is None:
                submission.manifest.extraction_warnings.append({"type": "missing_extractor", "artifact": file_path.name, "reason": artifact_type})
                continue
            try:
                evidence_list = extractor.extract(artifact)
                artifact.parse_status = "parsed"
                for evidence in evidence_list:
                    submission.add_evidence(evidence)
            except Exception as exc:  # pragma: no cover
                artifact.parse_status = "failed"
                submission.manifest.extraction_warnings.append({"type": "extraction_failure", "artifact": file_path.name, "reason": str(exc)})
        submission.processing_status["ingestion"] = "complete"
        submission.processing_status["extraction"] = "complete"
        return submission

    def _discover_files(self, root: Path) -> Iterable[Path]:
        return sorted(p for p in root.rglob("*") if p.is_file() and not p.name.startswith("."))

    def _expand_archives(self, root: Path) -> None:
        for file_path in list(root.rglob("*")):
            if not file_path.is_file():
                continue
            suffixes = [s.lower() for s in file_path.suffixes]
            if file_path.suffix.lower() == ".zip":
                target = file_path.with_suffix("")
                target.mkdir(exist_ok=True)
                with zipfile.ZipFile(file_path, "r") as zf:
                    self._safe_extract_zip(zf, target)
            elif suffixes[-2:] == [".tar", ".gz"] or file_path.suffix.lower() == ".tar":
                target = file_path.parent / file_path.stem
                target.mkdir(exist_ok=True)
                with tarfile.open(file_path, "r:*") as tf:
                    self._safe_extract_tar(tf, target)

    @staticmethod
    def _safe_extract_zip(zf: zipfile.ZipFile, target: Path) -> None:
        for member in zf.infolist():
            member_path = (target / member.filename).resolve()
            if not str(member_path).startswith(str(target.resolve())):
                raise ValueError("Unsafe zip archive path detected.")
        zf.extractall(target)

    @staticmethod
    def _safe_extract_tar(tf: tarfile.TarFile, target: Path) -> None:
        for member in tf.getmembers():
            member_path = (target / member.name).resolve()
            if not str(member_path).startswith(str(target.resolve())):
                raise ValueError("Unsafe tar archive path detected.")
        tf.extractall(target)

    @staticmethod
    def _checksum(path: Path) -> str:
        hasher = hashlib.sha256()
        with path.open("rb") as fh:
            while chunk := fh.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()
