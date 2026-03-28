from __future__ import annotations

from pathlib import Path
from typing import List
import wave

import cv2

from autograde.extractors.base import BaseExtractor
from autograde.models import Artifact, EvidenceObject, Location


def _find_sidecar_text(path: Path) -> str:
    candidates = [path.with_suffix('.txt'), path.with_suffix('.srt'), path.parent / f"{path.stem}.transcript.txt"]
    for cand in candidates:
        if cand.exists():
            return cand.read_text(encoding='utf-8', errors='ignore')
    return ""


class AudioMetadataExtractor(BaseExtractor):
    extractor_id = "audio_metadata_extractor_v1"
    supported_types = {"audio"}

    def extract(self, artifact: Artifact) -> List[EvidenceObject]:
        path = Path(artifact.storage_path)
        duration = None
        channels = None
        sample_rate = None
        confidence = 0.75
        if path.suffix.lower() == '.wav':
            with wave.open(str(path), 'rb') as wf:
                channels = wf.getnchannels()
                sample_rate = wf.getframerate()
                frames = wf.getnframes()
                duration = frames / float(sample_rate) if sample_rate else None
                confidence = 0.95
        transcript = _find_sidecar_text(path)
        evidence = [EvidenceObject(
            evidence_id=f"{artifact.artifact_id}_audio_meta_1",
            submission_id=artifact.submission_id,
            artifact_id=artifact.artifact_id,
            modality="audio",
            subtype="audio_metadata",
            content=None,
            structured_content={
                "duration_seconds": duration,
                "channels": channels,
                "sample_rate": sample_rate,
                "has_transcript": bool(transcript.strip()),
            },
            preview=path.name,
            location=Location(file=path.name),
            confidence=confidence,
            extractor_id=self.extractor_id,
            tags=["audio", "metadata"],
        )]
        if transcript.strip():
            evidence.append(EvidenceObject(
                evidence_id=f"{artifact.artifact_id}_audio_transcript_1",
                submission_id=artifact.submission_id,
                artifact_id=artifact.artifact_id,
                modality="text",
                subtype="audio_transcript",
                content=transcript,
                structured_content={"source_artifact_type": "audio"},
                preview=transcript[:120],
                location=Location(file=path.name),
                confidence=0.9,
                extractor_id=self.extractor_id,
                tags=["audio", "transcript"],
            ))
        return evidence


class VideoMetadataExtractor(BaseExtractor):
    extractor_id = "video_metadata_extractor_v1"
    supported_types = {"video"}

    def extract(self, artifact: Artifact) -> List[EvidenceObject]:
        path = Path(artifact.storage_path)
        cap = cv2.VideoCapture(str(path))
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        duration = frame_count / fps if fps else None
        ret, frame = cap.read()
        first_frame_mean = float(frame.mean()) if ret else None
        cap.release()
        transcript = _find_sidecar_text(path)
        evidence = [EvidenceObject(
            evidence_id=f"{artifact.artifact_id}_video_meta_1",
            submission_id=artifact.submission_id,
            artifact_id=artifact.artifact_id,
            modality="video",
            subtype="video_metadata",
            content=None,
            structured_content={
                "frame_count": frame_count,
                "fps": fps,
                "duration_seconds": duration,
                "width": width,
                "height": height,
                "first_frame_mean": first_frame_mean,
                "has_transcript": bool(transcript.strip()),
            },
            preview=path.name,
            location=Location(file=path.name),
            confidence=0.92,
            extractor_id=self.extractor_id,
            tags=["video", "metadata"],
        )]
        if transcript.strip():
            evidence.append(EvidenceObject(
                evidence_id=f"{artifact.artifact_id}_video_transcript_1",
                submission_id=artifact.submission_id,
                artifact_id=artifact.artifact_id,
                modality="text",
                subtype="video_transcript",
                content=transcript,
                structured_content={"source_artifact_type": "video"},
                preview=transcript[:120],
                location=Location(file=path.name),
                confidence=0.9,
                extractor_id=self.extractor_id,
                tags=["video", "transcript"],
            ))
        return evidence
