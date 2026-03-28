from autograde.evaluators.registry import EvaluatorRegistry
from autograde.rubric import Criterion, ScoringPolicy
from autograde.models import EvidenceObject


def _text_ev(eid: str, text: str):
    return EvidenceObject(evidence_id=eid, submission_id='s1', artifact_id='a1', modality='text', subtype='paragraph', content=text, location={'page':1}, confidence=0.95, extractor_id='unit')


def test_subject_hardening_demo():
    registry = EvaluatorRegistry()
    criterion = Criterion(
        criterion_id='E1',
        name='Thesis and evidence',
        description='Assess thesis clarity and textual support.',
        max_score=20,
        weight=1.0,
        required_modalities=['text'],
        evaluation_dimensions=['clarity','justification'],
        evaluator_hints=['thesis_strength','textual_evidence_usage'],
        scoring_policy=ScoringPolicy(mode='weighted_average'),
        metadata={
            'expected_concepts': [
                {'name': 'thesis', 'synonyms': ['claim', 'position'], 'required': True},
                {'name': 'interpretation', 'synonyms': ['suggests', 'reveals'], 'required': True},
            ]
        }
    )
    evidence = [
        _text_ev('ev1', 'This essay argues that the narrator reveals a fractured moral position because the scene repeatedly suggests divided loyalty.'),
        _text_ev('ev2', 'According to the text, the author writes that duty and desire collide; this evidence supports the central claim.'),
    ]
    thesis = registry.get('thesis_strength').evaluate(criterion, evidence)
    support = registry.get('textual_evidence_usage').evaluate(criterion, evidence)
    assert thesis.score > 0
    assert support.score > 0
    assert thesis.confidence >= 0.68
    assert any(flag['type'] == 'hybrid_evaluator' for flag in thesis.flags)
