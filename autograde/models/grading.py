from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(slots=True)
class EvaluatorResult:
    evaluator_id: str
    criterion_id: str
    score: float
    max_score: float
    confidence: float
    rationale: str
    supporting_evidence: List[str] = field(default_factory=list)
    flags: List[Dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class CriterionResult:
    criterion_id: str
    score: float
    max_score: float
    confidence: float
    rationale: str
    evaluator_results: List[EvaluatorResult] = field(default_factory=list)
    manual_review_required: bool = False
    evidence_ids: List[str] = field(default_factory=list)
    status: str = "graded"
    flags: List[Dict[str, Any]] = field(default_factory=list)
    cross_check_results: List[Dict[str, Any]] = field(default_factory=list)
    contradiction_results: List[Dict[str, Any]] = field(default_factory=list)
    claim_evidence_results: List[Dict[str, Any]] = field(default_factory=list)
    coverage_results: List[Dict[str, Any]] = field(default_factory=list)
    coverage_status: str = "covered"
    capability_status: str = "supported"
    support_status: str = "supported"
    confidence_factors: List[Dict[str, Any]] = field(default_factory=list)
    confidence_rationale: str = ""
    evidence_strength: float = 1.0
    effective_weight: float = 0.0
    contradiction_penalty: float = 0.0


@dataclass(slots=True)
class GradingResult:
    submission_id: str
    criterion_results: List[CriterionResult]
    final_score: float
    max_score: float
    review_flags: List[Dict[str, Any]] = field(default_factory=list)
    claim_graph_summary: Dict[str, Any] = field(default_factory=dict)
    review_bundles: List[Dict[str, Any]] = field(default_factory=list)
    rubric_warnings: List[Dict[str, Any]] = field(default_factory=list)
    explanations: List[Dict[str, Any]] = field(default_factory=list)
    global_failures: List[Dict[str, Any]] = field(default_factory=list)
