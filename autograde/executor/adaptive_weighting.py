from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Sequence

from autograde.models import CriterionResult
from autograde.rubric import Rubric


@dataclass(slots=True)
class AdaptiveWeightingDecision:
    criterion_id: str
    base_weight: float
    evidence_strength: float
    adjusted_weight: float
    factor: float
    rationale: str


class AdaptiveWeightingEngine:
    def apply(self, criterion_results: Sequence[CriterionResult], rubric: Rubric) -> list[AdaptiveWeightingDecision]:
        params: Dict[str, Any] = rubric.adaptive_weighting_params or {}
        min_factor = float(params.get("min_factor", 0.7))
        max_factor = float(params.get("max_factor", 1.3))
        confidence_weight = float(params.get("confidence_weight", 0.45))
        coverage_weight = float(params.get("coverage_weight", 0.25))
        support_weight = float(params.get("support_weight", 0.15))
        contradiction_weight = float(params.get("contradiction_weight", 0.15))
        decisions: list[AdaptiveWeightingDecision] = []
        for result in criterion_results:
            criterion = rubric.get_criterion(result.criterion_id)
            if criterion is None:
                continue
            base_weight = float(criterion.weight)
            evidence_strength, rationale = self._evidence_strength(
                result,
                confidence_weight=confidence_weight,
                coverage_weight=coverage_weight,
                support_weight=support_weight,
                contradiction_weight=contradiction_weight,
            )
            factor = min_factor + (max_factor - min_factor) * evidence_strength
            adjusted_weight = base_weight * factor
            decisions.append(AdaptiveWeightingDecision(
                criterion_id=result.criterion_id,
                base_weight=base_weight,
                evidence_strength=evidence_strength,
                adjusted_weight=adjusted_weight,
                factor=factor,
                rationale=rationale,
            ))
        return decisions

    def _evidence_strength(
        self,
        result: CriterionResult,
        *,
        confidence_weight: float,
        coverage_weight: float,
        support_weight: float,
        contradiction_weight: float,
    ) -> tuple[float, str]:
        confidence_component = max(0.0, min(1.0, float(result.confidence)))
        coverage_map = {
            "covered": 1.0,
            "partial": 0.7,
            "missing_required": 0.35,
        }
        coverage_component = coverage_map.get(result.coverage_status, 0.55)
        support_component = 1.0
        if result.capability_status == "unsupported" or result.status == "unsupported_needs_review":
            support_component = 0.1
        elif result.support_status == "partial" or result.status == "partially_graded":
            support_component = 0.55
        contradiction_component = 1.0
        contradicted = sum(1 for c in result.claim_evidence_results if c.get("status") == "contradicted")
        contradiction_component -= min(0.8, 0.25 * len(result.contradiction_results) + 0.2 * contradicted)
        contradiction_component = max(0.1, contradiction_component)
        if result.status in {"blocked", "insufficient_evidence", "escalated"}:
            support_component = min(support_component, 0.45)
        evidence_strength = (
            confidence_weight * confidence_component
            + coverage_weight * coverage_component
            + support_weight * support_component
            + contradiction_weight * contradiction_component
        )
        evidence_strength = max(0.0, min(1.0, evidence_strength))
        rationale = (
            f"Evidence strength combined confidence={confidence_component:.2f}, coverage={coverage_component:.2f}, "
            f"support={support_component:.2f}, contradiction_resilience={contradiction_component:.2f}."
        )
        return evidence_strength, rationale
