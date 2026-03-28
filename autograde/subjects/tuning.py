from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from autograde.rubric import Criterion, Rubric


@dataclass(slots=True)
class SubjectTuning:
    subject_id: str
    low_confidence_threshold: float | None = None
    review_bias: str = "balanced"  # less_review | balanced | more_review
    notes: List[str] = field(default_factory=list)

    def apply(self, rubric: Rubric) -> Rubric:
        tuned = Rubric(
            assignment_id=rubric.assignment_id,
            assignment_title=rubric.assignment_title,
            required_artifacts=list(rubric.required_artifacts),
            criteria=[self._tune_criterion(c) for c in rubric.criteria],
            aggregation_mode=rubric.aggregation_mode,
            normalize_to=rubric.normalize_to,
            low_confidence_threshold=self.low_confidence_threshold if self.low_confidence_threshold is not None else rubric.low_confidence_threshold,
        )
        return tuned

    def _tune_criterion(self, criterion: Criterion) -> Criterion:
        c = Criterion(**{f: getattr(criterion, f) for f in criterion.__dataclass_fields__})
        # shallow-copy mutables so the tuned rubric does not mutate the original profile templates.
        c.required_modalities = list(criterion.required_modalities)
        c.evaluation_dimensions = list(criterion.evaluation_dimensions)
        c.artifact_scope = list(criterion.artifact_scope)
        c.evaluator_hints = list(criterion.evaluator_hints)
        c.cross_checks = list(criterion.cross_checks)
        c.required_evidence_types = list(criterion.required_evidence_types)
        c.supporting_evidence_types = list(criterion.supporting_evidence_types)
        c.required_tags = list(criterion.required_tags)
        c.supporting_tags = list(criterion.supporting_tags)
        c.depends_on = list(criterion.depends_on)
        c.manual_review_conditions = list(criterion.manual_review_conditions)
        c.aspects = list(criterion.aspects)
        c.metadata = dict(criterion.metadata)

        if self.review_bias == 'less_review':
            if c.integrity_policy == 'review_only':
                c.integrity_policy = 'ignore' if c.weight <= 0.1 else 'review_only'
            if c.cross_check_policy == 'binding' and c.weight <= 0.2:
                c.cross_check_policy = 'advisory'
            if 'behavior' in c.evaluation_dimensions or 'implementation_alignment' in c.evaluation_dimensions:
                c.metadata['calibration_note'] = 'less_review_tuned'
        elif self.review_bias == 'more_review':
            if c.integrity_policy == 'ignore':
                c.integrity_policy = 'review_only'
            if c.cross_checks and c.cross_check_policy == 'advisory':
                c.cross_check_policy = 'binding' if c.weight >= 0.15 else 'advisory'
            if c.weight >= 0.2 and 'low_confidence' not in c.manual_review_conditions:
                c.manual_review_conditions.append('low_confidence')
            c.metadata['calibration_note'] = 'more_review_tuned'
        return c


def tuning_from_mapping(subject_id: str, mapping: Dict[str, object]) -> SubjectTuning:
    return SubjectTuning(
        subject_id=subject_id,
        low_confidence_threshold=float(mapping.get('low_confidence_threshold')) if mapping.get('low_confidence_threshold') is not None else None,
        review_bias=str(mapping.get('review_bias', 'balanced')),
        notes=list(mapping.get('notes', [])),
    )
