from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List

from autograde.llm.client import get_default_llm_client
from autograde.llm.prompt_builder import build_rubric_induction_prompt
from autograde.rubric.schema import Criterion, Rubric, ScoringPolicy
from autograde.rubric.validator import RubricValidator


@dataclass(slots=True)
class PastCase:
    submission_summary: str
    feedback: str
    score: float


@dataclass(slots=True)
class InducedCriterion:
    name: str
    description: str
    weight: float
    evaluators: List[str]


ALIASES = {
    'clarity_of_explanation': 'explanation',
    'quality_of_explanation': 'explanation',
    'correctness_of_solution': 'correctness',
    'technical_correctness': 'correctness',
    'analysis_depth': 'analysis',
    'depth_of_analysis': 'analysis',
    'originality_of_work': 'originality',
    'methodology_quality': 'methodology',
    'results_interpretation': 'interpretation',
}

ALLOWED_EVALUATORS = {
    'subjective_reasoning', 'argument_quality', 'proof_explanation', 'design_justification',
    'behavioral_correctness', 'implementation_report_alignment', 'result_analysis',
    'text_quality', 'argumentation', 'technical_correctness', 'requirements_coverage',
    'cross_modal_consistency', 'citation_integrity', 'subjective_answer_quality',
}


def _canonical_name(name: str) -> str:
    s = name.strip().lower().replace('-', '_').replace(' ', '_')
    return ALIASES.get(s, s)


def _canonical_evaluators(evaluators: Iterable[str]) -> List[str]:
    out: List[str] = []
    for evaluator in evaluators:
        ev = str(evaluator).strip()
        if ev in ALLOWED_EVALUATORS and ev not in out:
            out.append(ev)
    if not out:
        out.append('subjective_reasoning')
    return out


def _merge_llm_criteria(raw_criteria: List[Dict[str, Any]]) -> List[InducedCriterion]:
    merged: Dict[str, Dict[str, Any]] = {}
    for item in raw_criteria:
        try:
            name = _canonical_name(str(item.get('name', 'criterion')))
            weight = max(0.0, float(item.get('weight', 0.0)))
            description = str(item.get('description', '')).strip()
            evaluators = _canonical_evaluators(item.get('evaluators', []))
        except Exception:
            continue
        if not name:
            continue
        bucket = merged.setdefault(name, {'name': name, 'weight': 0.0, 'description': description, 'evaluators': []})
        bucket['weight'] += weight
        if description and len(description) > len(bucket['description']):
            bucket['description'] = description
        for evaluator in evaluators:
            if evaluator not in bucket['evaluators']:
                bucket['evaluators'].append(evaluator)
    total = sum(float(v['weight']) for v in merged.values()) or 1.0
    induced: List[InducedCriterion] = []
    for value in merged.values():
        induced.append(InducedCriterion(
            name=value['name'],
            description=value['description'] or f"Assess {value['name'].replace('_', ' ')}.",
            weight=float(value['weight']) / total,
            evaluators=value['evaluators'] or ['subjective_reasoning'],
        ))
    induced.sort(key=lambda c: c.weight, reverse=True)
    return induced


def _subject_modalities(subject_profile: str) -> List[str]:
    mapping = {
        'programming': ['text', 'code'],
        'humanities': ['text', 'citation'],
        'engineering': ['text', 'diagram', 'table'],
        'mathematics': ['text', 'equation'],
        'lab_science': ['text', 'table'],
    }
    return mapping.get(subject_profile, ['text'])


def _to_rubric(criteria_data: List[InducedCriterion], subject_profile: str, title: str) -> Rubric:
    criteria: List[Criterion] = []
    required_modalities = _subject_modalities(subject_profile)
    for idx, criterion in enumerate(criteria_data, start=1):
        dims: List[str] = []
        if criterion.name in {'correctness', 'proof', 'proof_quality'}:
            dims.append('correctness')
        if criterion.name in {'explanation', 'analysis', 'interpretation', 'argument', 'structure'}:
            dims.append('clarity')
        if criterion.name in {'originality'}:
            dims.append('consistency')
        if not dims:
            dims = ['clarity']
        criteria.append(
            Criterion(
                criterion_id=f'I{idx}',
                name=criterion.name.replace('_', ' ').title(),
                description=criterion.description,
                max_score=10.0,
                weight=criterion.weight,
                required_modalities=list(required_modalities),
                evaluation_dimensions=dims,
                evaluator_hints=list(criterion.evaluators),
                minimum_evidence_count=1,
                scoring_policy=ScoringPolicy(mode='weighted_average'),
                metadata={'induced': True, 'source': 'llm_deterministic_induction', 'subject_profile': subject_profile},
            )
        )
    rubric = Rubric(
        assignment_id=f'induced_{subject_profile}',
        assignment_title=title,
        required_artifacts=['report'],
        criteria=criteria,
        aggregation_mode='weighted_sum',
        normalize_to=100.0,
    )
    validation = RubricValidator().validate(rubric)
    if not validation.is_valid:
        raise ValueError(f'Induced rubric invalid: {validation.errors}')
    return rubric


class RubricInducer:
    def __init__(self) -> None:
        self.client = get_default_llm_client()

    def induce(self, past_cases: List[PastCase], subject_profile: str) -> Rubric:
        prompt = build_rubric_induction_prompt(past_cases=past_cases, subject_profile=subject_profile)
        raw = self.client.complete_json(
            request=type('Req', (), {
                'evaluator_id': 'llm_rubric_induction',
                'criterion_id': 'rubric_induction',
                'prompt': prompt,
                'evidence_refs': [],
                'metadata': {'subject_profile': subject_profile},
            })()
        )
        raw_criteria = raw.get('criteria', []) if isinstance(raw, dict) else []
        merged = _merge_llm_criteria(raw_criteria)
        if not merged:
            merged = [
                InducedCriterion('correctness', 'Assess whether the submission satisfies the core task requirements.', 0.5, ['subjective_reasoning']),
                InducedCriterion('explanation', 'Assess clarity and support of the explanation.', 0.3, ['subjective_reasoning']),
                InducedCriterion('analysis', 'Assess analysis, interpretation, or discussion quality.', 0.2, ['argument_quality']),
            ]
        return _to_rubric(merged, subject_profile=subject_profile, title=f'Induced {subject_profile} rubric')


def induce_rubric_from_past_cases(past_cases: List[PastCase], subject_profile: str, use_llm: bool = True) -> Rubric:
    if not use_llm:
        raise ValueError('This induction path is designed for LLM + deterministic consolidation.')
    return RubricInducer().induce(past_cases, subject_profile)
