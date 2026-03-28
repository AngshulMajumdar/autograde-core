from __future__ import annotations

from typing import Any, Dict

from autograde.models import CriterionResult


def build_score_explanation(result: CriterionResult) -> Dict[str, Any]:
    contradiction_penalty = round(getattr(result, "contradiction_penalty", 0.0), 4)
    return {
        "criterion_id": result.criterion_id,
        "status": result.status,
        "base_score": result.score,
        "confidence": result.confidence,
        "capability_status": result.capability_status,
        "support_status": result.support_status,
        "coverage_status": result.coverage_status,
        "evidence_strength": result.evidence_strength,
        "effective_weight": result.effective_weight,
        "contradiction_penalty_estimate": contradiction_penalty,
        "final_contribution_estimate": round(result.score * result.effective_weight, 6),
        "evidence_ids": list(result.evidence_ids),
        "flags": list(result.flags),
    }
