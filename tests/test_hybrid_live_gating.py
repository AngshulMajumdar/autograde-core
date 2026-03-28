from autograde.evaluators.registry import EvaluatorRegistry
from autograde.models import EvidenceObject
from autograde.rubric.schema import Criterion


def test_hybrid_ignores_mock_llm_when_not_live():
    registry = EvaluatorRegistry()
    evaluator = registry.get('thesis_strength')
    criterion = Criterion(criterion_id='C1', name='Thesis', description='Evaluate thesis', max_score=10.0, weight=1.0, required_modalities=['text'], evaluation_dimensions=['coherence'], metadata={'expected_concepts': [{'name': 'justice', 'required': True}]})
    evidence = [EvidenceObject(evidence_id='e1', submission_id='s1', artifact_id='a1', modality='text', subtype='essay', content='This essay argues that justice requires equal access because institutions shape opportunity.', structured_content={}, preview='', location={'page': 1}, confidence=1.0, extractor_id='x', tags=[], links=[])]
    result = evaluator.evaluate(criterion, evidence)
    fallback_flags = [f for f in result.flags if f.get('type') == 'hybrid_llm_fallback']
    assert fallback_flags
    assert fallback_flags[0]['reason'] == 'live_llm_unavailable'
