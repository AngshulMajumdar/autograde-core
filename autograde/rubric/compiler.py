from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from autograde.rubric.schema import Criterion, Rubric


DIMENSION_TO_EVALUATOR: Dict[str, str] = {
    "clarity": "text_quality",
    "coherence": "argumentation",
    "organization": "text_quality",
    "correctness": "technical_correctness",
    "completeness": "requirements_coverage",
    "consistency": "cross_modal_consistency",
    "citation_quality": "citation_integrity",
    "justification": "argumentation",
    "behavior": "behavioral_correctness",
    "implementation_alignment": "implementation_report_alignment",
}


@dataclass(slots=True)
class EvidenceQueryPlan:
    required_modalities: List[str] = field(default_factory=list)
    artifact_scope: List[str] = field(default_factory=list)
    required_evidence_types: List[str] = field(default_factory=list)
    supporting_evidence_types: List[str] = field(default_factory=list)
    required_tags: List[str] = field(default_factory=list)
    supporting_tags: List[str] = field(default_factory=list)
    minimum_evidence_count: int = 1


@dataclass(slots=True)
class CriterionNode:
    criterion: Criterion
    evaluators: List[str] = field(default_factory=list)
    query_plan: EvidenceQueryPlan = field(default_factory=EvidenceQueryPlan)
    dependencies: List[str] = field(default_factory=list)


@dataclass(slots=True)
class GradingGraph:
    nodes: List[CriterionNode]


class RubricCompiler:
    def compile(self, rubric: Rubric) -> GradingGraph:
        nodes: List[CriterionNode] = []
        for criterion in rubric.criteria:
            evaluators = list(criterion.evaluator_hints)
            for dim in criterion.evaluation_dimensions:
                evaluator = DIMENSION_TO_EVALUATOR.get(dim)
                if evaluator and evaluator not in evaluators:
                    evaluators.append(evaluator)
            if not evaluators:
                evaluators.append("requirements_coverage")
            query_plan = EvidenceQueryPlan(
                required_modalities=list(criterion.required_modalities),
                artifact_scope=list(criterion.artifact_scope),
                required_evidence_types=list(criterion.required_evidence_types),
                supporting_evidence_types=list(criterion.supporting_evidence_types),
                required_tags=list(criterion.required_tags),
                supporting_tags=list(criterion.supporting_tags),
                minimum_evidence_count=max(criterion.minimum_evidence_count, 1),
            )
            nodes.append(
                CriterionNode(
                    criterion=criterion,
                    evaluators=evaluators,
                    query_plan=query_plan,
                    dependencies=list(criterion.depends_on),
                )
            )
        return GradingGraph(nodes=nodes)
