from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from autograde.capabilities import CAPABILITY_REGISTRY, CapabilityLevel, describe_capability
from autograde.executor.evidence_query import EvidenceBundle
from autograde.rubric import Criterion


@dataclass(slots=True)
class CapabilityAssessment:
    capability_status: str
    support_status: str
    confidence: float
    rationale: str
    flags: List[Dict[str, object]] = field(default_factory=list)


class ModalityCapabilityRegistry:
    """Conservative registry describing current engine support by modality."""

    def support_for(self, modality: str) -> str:
        return describe_capability(CAPABILITY_REGISTRY.get(modality, CapabilityLevel.NONE))

    def level_for(self, modality: str) -> CapabilityLevel:
        return CAPABILITY_REGISTRY.get(modality, CapabilityLevel.NONE)


class CapabilityGatingEngine:
    def __init__(self) -> None:
        self.registry = ModalityCapabilityRegistry()

    def assess(self, criterion: Criterion, evidence_bundle: EvidenceBundle) -> CapabilityAssessment:
        required = list(criterion.required_modalities)
        if not required:
            return CapabilityAssessment(
                capability_status="supported",
                support_status="supported",
                confidence=1.0,
                rationale="No modality gating constraints specified.",
            )

        evidence_by_modality: Dict[str, list] = {}
        for ev in evidence_bundle.evidence:
            evidence_by_modality.setdefault(ev.modality, []).append(ev)

        missing_modalities: List[str] = []
        weak_modalities: List[str] = []
        unsupported_modalities: List[str] = []
        low_conf_modalities: List[str] = []

        for modality in required:
            level = self.registry.level_for(modality)
            if level <= CapabilityLevel.NONE:
                unsupported_modalities.append(modality)
                continue
            evs = evidence_by_modality.get(modality, [])
            if not evs:
                missing_modalities.append(modality)
                continue
            avg_conf = sum(ev.confidence for ev in evs) / max(len(evs), 1)
            if level in {CapabilityLevel.WEAK, CapabilityLevel.PARTIAL}:
                weak_modalities.append(modality)
            if avg_conf < 0.55:
                low_conf_modalities.append(modality)

        flags: List[Dict[str, object]] = []
        capability_status = "supported"
        support_status = "supported"
        confidence = 0.9
        rationale_parts: List[str] = []

        if unsupported_modalities:
            capability_status = "unsupported"
            support_status = "unsupported"
            confidence = 0.15
            flags.append({
                "type": "unsupported_modality",
                "modalities": unsupported_modalities,
                "severity": "high",
            })
            rationale_parts.append(
                f"Current engine support is not sufficient for modality/modalities: {', '.join(sorted(unsupported_modalities))}."
            )

        if missing_modalities:
            support_status = "partial" if capability_status == "supported" else support_status
            confidence = min(confidence, 0.45)
            flags.append({
                "type": "missing_required_modality",
                "modalities": missing_modalities,
                "severity": "high",
            })
            rationale_parts.append(
                f"Required modality evidence missing for: {', '.join(sorted(missing_modalities))}."
            )

        if weak_modalities:
            support_status = "partial" if support_status == "supported" else support_status
            confidence = min(confidence, 0.35)
            flags.append({
                "type": "partial_modality_support",
                "modalities": weak_modalities,
                "severity": "medium",
            })
            rationale_parts.append(
                f"Modality support is weak or partial for: {', '.join(sorted(weak_modalities))}."
            )

        if low_conf_modalities:
            support_status = "partial" if support_status == "supported" else support_status
            confidence = min(confidence, 0.5)
            flags.append({
                "type": "low_confidence_modality_evidence",
                "modalities": low_conf_modalities,
                "severity": "medium",
            })
            rationale_parts.append(
                f"Evidence confidence is low for: {', '.join(sorted(low_conf_modalities))}."
            )

        if not rationale_parts:
            rationale_parts.append("Required modalities are supported and present in the evidence bundle.")

        return CapabilityAssessment(
            capability_status=capability_status,
            support_status=support_status,
            confidence=confidence,
            rationale=" ".join(rationale_parts),
            flags=flags,
        )
