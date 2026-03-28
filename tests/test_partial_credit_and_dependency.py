from autograde.executor.partial_credit import PartialCreditEngine
from autograde.executor.dependency_logic import DependencyLogicEngine
from autograde.executor.scoring_policies import ScoringPolicyEngine
from autograde.models.grading import EvaluatorResult, CriterionResult
from autograde.rubric.schema import Criterion, CriterionSubcomponent, ScoringPolicy


def test_partial_credit_engine_computes_weighted_subcomponents():
    criterion = Criterion(
        criterion_id='C1', name='training', description='training', max_score=10, weight=1.0,
        required_modalities=['text'], evaluation_dimensions=['correctness'],
        subcomponents=[
            CriterionSubcomponent(name='split', evaluator_id='dataset_split', weight=1.0, required=True),
            CriterionSubcomponent(name='fit', evaluator_id='training_call', weight=2.0, required=True),
            CriterionSubcomponent(name='validation', evaluator_id='validation_strategy', weight=1.0, required=False),
        ],
    )
    results = [
        EvaluatorResult('dataset_split', 'C1', 10, 10, 0.9, 'ok'),
        EvaluatorResult('training_call', 'C1', 5, 10, 0.9, 'partial'),
    ]
    engine = PartialCreditEngine()
    decision = engine.compute(criterion, results)
    assert decision is not None
    assert decision.score == 5.0  # (1*1 + 0.5*2 + 0*1)/4 * 10
    assert 'split=1.00' in decision.rationale
    assert 'fit=0.50' in decision.rationale


def test_dependency_logic_caps_downstream_when_prereq_is_weak():
    criterion = Criterion(
        criterion_id='C2', name='analysis', description='analysis', max_score=10, weight=1.0,
        required_modalities=['text'], evaluation_dimensions=['correctness'],
        depends_on=['C1'], metadata={'dependency_min_fraction': 0.8, 'dependency_cap_fraction': 0.5},
    )
    completed = {
        'C1': CriterionResult('C1', score=6.0, max_score=10.0, confidence=0.8, rationale='weak prereq'),
    }
    logic = DependencyLogicEngine()
    decision = logic.assess(criterion, completed)
    assert decision.blocked is False
    assert decision.cap_fraction == 0.5


def test_scoring_policy_applies_partial_credit_and_dependency_cap():
    criterion = Criterion(
        criterion_id='C3', name='pipeline', description='pipeline', max_score=10, weight=1.0,
        required_modalities=['text'], evaluation_dimensions=['correctness'], scoring_policy=ScoringPolicy(mode='analytic_bands'),
        subcomponents=[
            CriterionSubcomponent(name='part_a', evaluator_id='a', weight=1.0, required=True),
            CriterionSubcomponent(name='part_b', evaluator_id='b', weight=1.0, required=True),
            CriterionSubcomponent(name='part_c', evaluator_id='c', weight=1.0, required=False),
        ],
    )
    results = [
        EvaluatorResult('a', 'C3', 10, 10, 0.9, 'ok'),
        EvaluatorResult('b', 'C3', 10, 10, 0.9, 'ok'),
    ]
    score, rationale = ScoringPolicyEngine().score(
        criterion,
        results,
        sufficiency_status='sufficient',
        dependency_cap_fraction=0.5,
        coverage_status='covered',
        coverage_score=1.0,
    )
    assert score == 5.0
    assert 'Partial-credit scoring used criterion subcomponents' in rationale
    assert 'Dependency rules capped the score' in rationale
