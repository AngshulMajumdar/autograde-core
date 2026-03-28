from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from autograde.models import CriterionResult


@dataclass(slots=True)
class ReviewBundle:
    criterion_id: str
    reason: str
    evidence_ids: List[str] = field(default_factory=list)
    flags: List[Dict[str, Any]] = field(default_factory=list)
    suggested_action: str = "manual_review"
    priority: str = "medium"
    priority_score: int = 50


class ReviewBundleBuilder:
    def build_for_criterion(self, result: CriterionResult) -> ReviewBundle | None:
        if not result.manual_review_required and result.status == "graded":
            return None
        reason = self._reason(result)
        priority, priority_score = self._priority(result)
        return ReviewBundle(
            criterion_id=result.criterion_id,
            reason=(reason + " " + result.confidence_rationale).strip(),
            evidence_ids=list(result.evidence_ids),
            flags=list(result.flags),
            suggested_action="manual_review",
            priority=priority,
            priority_score=priority_score,
        )

    @staticmethod
    def _reason(result: CriterionResult) -> str:
        if result.status == "unsupported_needs_review":
            return "Criterion relies on unsupported or only partially supported modalities."
        if result.status == "partially_graded":
            return "Criterion was only partially gradeable and needs instructor confirmation."
        if result.status == "blocked":
            return "Criterion was blocked by a dependency failure."
        if result.status == "insufficient_evidence":
            return "Criterion lacks enough reliable evidence for confident grading."
        if result.status == "escalated":
            return "Criterion has contradictions, cross-check failures, or integrity interactions requiring review."
        return "Criterion was flagged for low-confidence or policy-based manual review."

    @staticmethod
    def _priority(result: CriterionResult) -> tuple[str, int]:
        score = 0
        severities = [str(flag.get('severity', '')).lower() for flag in result.flags]
        if result.status == 'unsupported_needs_review':
            score += 75
        elif result.status == 'escalated':
            score += 65
        elif result.status == 'blocked':
            score += 55
        elif result.status == 'insufficient_evidence':
            score += 45
        elif result.status == 'partially_graded':
            score += 35
        else:
            score += 25

        if 'critical' in severities:
            score += 25
        elif 'high' in severities:
            score += 20
        elif 'medium' in severities:
            score += 10

        contradiction_count = len(result.contradiction_results)
        if contradiction_count:
            score += min(20, contradiction_count * 6)
        cross_failures = sum(1 for cc in result.cross_check_results if not cc.get('passed', True))
        if cross_failures:
            score += min(15, cross_failures * 5)
        if result.confidence < 0.35:
            score += 15
        elif result.confidence < 0.5:
            score += 8
        if result.capability_status == 'unsupported':
            score += 15
        elif result.capability_status == 'partial':
            score += 6

        if score >= 85:
            return 'critical', score
        if score >= 65:
            return 'high', score
        if score >= 40:
            return 'medium', score
        return 'low', score
