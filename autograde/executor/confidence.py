from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Sequence

from autograde.coverage.coverage_checker import CoverageAssessment
from autograde.executor.arbitration import ArbitrationResult
from autograde.executor.capability import CapabilityAssessment
from autograde.executor.contradiction_detector import ContradictionReport
from autograde.executor.evidence_sufficiency import EvidenceSufficiencyResult
from autograde.models import EvaluatorResult


@dataclass(slots=True)
class ConfidenceCalibrationResult:
    confidence: float
    factors: List[Dict[str, Any]] = field(default_factory=list)
    rationale: str = ""


class ConfidenceCalibrator:
    def calibrate(
        self,
        *,
        evaluator_results: Sequence[EvaluatorResult],
        sufficiency: EvidenceSufficiencyResult,
        capability: CapabilityAssessment,
        coverage: CoverageAssessment,
        contradiction_report: ContradictionReport,
        arbitration: ArbitrationResult,
    ) -> ConfidenceCalibrationResult:
        confidence = float(arbitration.confidence)
        factors: list[dict[str, Any]] = []

        if not evaluator_results:
            confidence *= 0.0
            factors.append({"factor": "no_evaluators", "effect": "critical"})

        evidence_count = len({eid for r in evaluator_results for eid in r.supporting_evidence})
        if evidence_count >= 4:
            confidence *= 1.03
            factors.append({"factor": "evidence_depth", "effect": "boost", "count": evidence_count})
        elif evidence_count <= 1:
            confidence *= 0.92
            factors.append({"factor": "thin_evidence", "effect": "penalty", "count": evidence_count})

        if sufficiency.status == 'ambiguous':
            confidence *= 0.85
            factors.append({"factor": "ambiguous_evidence", "effect": "penalty"})
        elif sufficiency.status == 'insufficient':
            confidence *= 0.55
            factors.append({"factor": "insufficient_evidence", "effect": "strong_penalty"})

        if capability.capability_status == 'unsupported':
            confidence *= 0.4
            factors.append({"factor": "unsupported_modality", "effect": "strong_penalty"})
        elif capability.support_status == 'partial':
            confidence *= 0.8
            factors.append({"factor": "partial_modality_support", "effect": "penalty"})

        if coverage.overall_status == 'covered':
            confidence *= 1.02
            factors.append({"factor": "good_coverage", "effect": "boost"})
        elif coverage.overall_status == 'missing_required':
            confidence *= 0.75
            factors.append({"factor": "missing_required_aspects", "effect": "penalty"})
        elif coverage.overall_status == 'weak_required':
            confidence *= 0.88
            factors.append({"factor": "weak_required_aspects", "effect": "penalty"})

        if contradiction_report.severity == 'high':
            confidence *= 0.7
            factors.append({"factor": "high_contradictions", "effect": "penalty"})
        elif contradiction_report.severity == 'medium':
            confidence *= 0.82
            factors.append({"factor": "medium_contradictions", "effect": "penalty"})

        confidence = max(0.0, min(1.0, confidence))
        rationale = self._summarize(factors)
        return ConfidenceCalibrationResult(confidence=round(confidence, 3), factors=factors, rationale=rationale)

    @staticmethod
    def _summarize(factors: Sequence[Dict[str, Any]]) -> str:
        if not factors:
            return "Confidence remained stable after calibration."
        labels = []
        for factor in factors[:5]:
            name = str(factor.get('factor', 'factor')).replace('_', ' ')
            effect = factor.get('effect', 'adjustment')
            labels.append(f"{name} ({effect})")
        return "Confidence calibration considered: " + ", ".join(labels) + "."
