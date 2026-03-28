from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from autograde.executor.evidence_query import EvidenceBundle
from autograde.rubric import Criterion


@dataclass(slots=True)
class EvidenceSufficiencyResult:
    status: str
    confidence: float
    rationale: str
    missing_modalities: list[str] = field(default_factory=list)
    low_confidence_evidence_ids: list[str] = field(default_factory=list)
    conflicting_evidence_ids: list[str] = field(default_factory=list)
    flags: list[Dict[str, Any]] = field(default_factory=list)


class EvidenceSufficiencyChecker:
    def __init__(self, low_confidence_threshold: float = 0.6, blocking_confidence_threshold: float = 0.4) -> None:
        self.low_confidence_threshold = low_confidence_threshold
        self.blocking_confidence_threshold = blocking_confidence_threshold

    def assess(self, criterion: Criterion, evidence_bundle: EvidenceBundle) -> EvidenceSufficiencyResult:
        evidence = list(evidence_bundle.evidence)
        required_modalities = set(criterion.required_modalities)
        present = {e.modality for e in evidence}
        missing = sorted(required_modalities - present)
        low_conf_ids = [e.evidence_id for e in evidence if e.confidence < self.low_confidence_threshold]
        blocking_low_conf = [e.evidence_id for e in evidence if e.confidence < self.blocking_confidence_threshold]
        flags: list[Dict[str, Any]] = []

        if missing:
            flags.append({"type": "missing_modality", "required": missing})
        if evidence_bundle.missing_requirements:
            flags.append({"type": "missing_required_evidence", "items": list(evidence_bundle.missing_requirements)})
        if low_conf_ids:
            flags.append({"type": "low_confidence_evidence", "evidence_ids": low_conf_ids})

        if not evidence:
            return EvidenceSufficiencyResult(
                status="insufficient",
                confidence=0.0,
                rationale="No evidence matched this criterion.",
                missing_modalities=missing,
                flags=flags,
            )

        avg_conf = sum(e.confidence for e in evidence) / len(evidence)
        insufficient_conditions = bool(missing) or bool(evidence_bundle.missing_requirements)
        if insufficient_conditions:
            status = "insufficient"
            rationale = "Required evidence was missing for this criterion."
            confidence = min(avg_conf, 0.45)
        elif blocking_low_conf:
            status = "ambiguous"
            rationale = "Evidence exists, but some direct evidence is too low-confidence for reliable grading."
            confidence = min(avg_conf, 0.5)
        elif low_conf_ids:
            status = "ambiguous"
            rationale = "Evidence exists, but some extracted items have low confidence."
            confidence = min(avg_conf, 0.7)
        else:
            status = "sufficient"
            rationale = f"Sufficient evidence was found for this criterion ({evidence_bundle.query_summary})."
            confidence = avg_conf

        return EvidenceSufficiencyResult(
            status=status,
            confidence=round(confidence, 3),
            rationale=rationale,
            missing_modalities=missing,
            low_confidence_evidence_ids=low_conf_ids,
            flags=flags,
        )
