from __future__ import annotations

from autograde.rubric import Criterion, Rubric, ScoringPolicy


def build_demo_rubric() -> Rubric:
    return Rubric(
        assignment_id='CS301_A2',
        assignment_title='Data Structures Project',
        required_artifacts=['report', 'source_code'],
        criteria=[
            Criterion(
                criterion_id='C1',
                name='Report quality',
                description='Assess clarity and argument quality in the report.',
                max_score=20,
                weight=0.4,
                required_modalities=['text'],
                evaluation_dimensions=['clarity', 'coherence'],
                artifact_scope=['report', 'text'],
                scoring_policy=ScoringPolicy(mode='analytic_bands'),
            ),
            Criterion(
                criterion_id='C2',
                name='Implementation quality',
                description='Assess code quality and correctness signals.',
                max_score=20,
                weight=0.4,
                required_modalities=['code'],
                evaluation_dimensions=['correctness'],
                evaluator_hints=['code_quality'],
                artifact_scope=['source_code', 'notebook'],
                scoring_policy=ScoringPolicy(mode='gated_score', params={'gate_evaluator': 'technical_correctness', 'gate_threshold': 0.5, 'cap_fraction': 0.4}),
            ),
            Criterion(
                criterion_id='C3',
                name='Report-code consistency',
                description='Assess whether report and code align conceptually.',
                max_score=10,
                weight=0.2,
                required_modalities=['text', 'code'],
                evaluation_dimensions=['consistency'],
                artifact_scope=['report', 'source_code', 'notebook'],
                scoring_policy=ScoringPolicy(mode='weighted_average'),
            ),
        ],
        normalize_to=100.0,
    )


def rubric_to_payload(rubric: Rubric) -> dict:
    return {
        'assignment_id': rubric.assignment_id,
        'assignment_title': rubric.assignment_title,
        'required_artifacts': rubric.required_artifacts,
        'criteria': [
            {
                'criterion_id': c.criterion_id,
                'name': c.name,
                'description': c.description,
                'max_score': c.max_score,
                'weight': c.weight,
                'required_modalities': c.required_modalities,
                'evaluation_dimensions': c.evaluation_dimensions,
                'artifact_scope': c.artifact_scope,
                'evaluator_hints': c.evaluator_hints,
                'cross_checks': c.cross_checks,
                'required_evidence_types': c.required_evidence_types,
                'supporting_evidence_types': c.supporting_evidence_types,
                'required_tags': c.required_tags,
                'supporting_tags': c.supporting_tags,
                'minimum_evidence_count': c.minimum_evidence_count,
                'zero_if_missing': c.zero_if_missing,
                'cross_check_policy': c.cross_check_policy,
                'contradiction_policy': c.contradiction_policy,
                'contradiction_severity_threshold': c.contradiction_severity_threshold,
                'depends_on': c.depends_on,
                'manual_review_conditions': c.manual_review_conditions,
                'scoring_policy': {'mode': c.scoring_policy.mode, 'params': c.scoring_policy.params},
                'integrity_policy': c.integrity_policy,
                'integrity_scope': c.integrity_scope,
                'integrity_severity_threshold': c.integrity_severity_threshold,
                'metadata': c.metadata,
            }
            for c in rubric.criteria
        ],
        'aggregation_mode': rubric.aggregation_mode,
        'normalize_to': rubric.normalize_to,
        'low_confidence_threshold': rubric.low_confidence_threshold,
        'adaptive_weighting_enabled': rubric.adaptive_weighting_enabled,
        'adaptive_weighting_params': rubric.adaptive_weighting_params,
    }
