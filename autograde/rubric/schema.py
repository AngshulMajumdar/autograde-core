from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from autograde.coverage.aspect_model import CriterionAspect


@dataclass(slots=True)
class ScoringPolicy:
    mode: str = "analytic_bands"
    params: Dict[str, Any] = field(default_factory=dict)




@dataclass(slots=True)
class CriterionSubcomponent:
    name: str
    evaluator_id: str
    weight: float = 1.0
    required: bool = False

@dataclass(slots=True)
class Criterion:
    criterion_id: str
    name: str
    description: str
    max_score: float
    weight: float
    required_modalities: List[str]
    evaluation_dimensions: List[str]
    artifact_scope: List[str] = field(default_factory=list)
    evaluator_hints: List[str] = field(default_factory=list)
    cross_checks: List[str] = field(default_factory=list)
    required_evidence_types: List[str] = field(default_factory=list)
    supporting_evidence_types: List[str] = field(default_factory=list)
    required_tags: List[str] = field(default_factory=list)
    supporting_tags: List[str] = field(default_factory=list)
    minimum_evidence_count: int = 1
    zero_if_missing: bool = False
    cross_check_policy: str = "advisory"  # advisory | binding
    contradiction_policy: str = "discount"  # review_only | discount | block_if_high
    contradiction_severity_threshold: str = "medium"  # low | medium | high
    depends_on: List[str] = field(default_factory=list)
    manual_review_conditions: List[str] = field(default_factory=list)
    scoring_policy: ScoringPolicy = field(default_factory=ScoringPolicy)
    integrity_policy: str = "review_only"  # ignore | review_only | discount_if_relevant | block_if_high
    integrity_scope: str = "auto"  # auto | text | code | all
    integrity_severity_threshold: str = "medium"
    aspects: List[CriterionAspect] = field(default_factory=list)
    subcomponents: List[CriterionSubcomponent] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Rubric:
    assignment_id: str
    assignment_title: str
    required_artifacts: List[str]
    criteria: List[Criterion]
    aggregation_mode: str = "weighted_sum"
    normalize_to: float = 100.0
    low_confidence_threshold: float = 0.65
    adaptive_weighting_enabled: bool = False
    adaptive_weighting_params: Dict[str, Any] = field(default_factory=dict)

    def get_criterion(self, criterion_id: str) -> Optional[Criterion]:
        for criterion in self.criteria:
            if criterion.criterion_id == criterion_id:
                return criterion
        return None
