from autograde.executor.arbitration import ArbitrationPolicy
from autograde.executor.contradiction_detector import ContradictionReport, ContradictionResult
from autograde.models import EvaluatorResult
from autograde.rubric import Criterion, ScoringPolicy


def _criterion(policy='discount', threshold='medium'):
    return Criterion(
        criterion_id='C1',
        name='consistency',
        description='Consistency criterion',
        max_score=10.0,
        weight=1.0,
        required_modalities=['text'],
        evaluation_dimensions=['correctness'],
        scoring_policy=ScoringPolicy(mode='analytic_bands'),
        contradiction_policy=policy,
        contradiction_severity_threshold=threshold,
    )


def _evals():
    return [EvaluatorResult('deterministic_test','C1',8.0,10.0,0.9,'ok',[],[])]


def _report(severity='high', subtype='algorithm_mismatch', n=1):
    contradictions = [
        ContradictionResult(
            contradiction_type=subtype,
            passed=False,
            confidence=0.9,
            rationale='bad contradiction',
            evidence_ids=['e1'],
            flags=[{'type':'contradiction','subtype':subtype,'severity':severity}],
        )
        for _ in range(n)
    ]
    return ContradictionReport(
        contradictions=contradictions,
        severity=severity,
        confidence=0.9,
        rationale='contradictions found',
        flags=[{'type':'contradiction','subtype':subtype,'severity':severity}] * n,
    )


def test_discount_policy_applies_real_penalty():
    arb = ArbitrationPolicy()
    res = arb.resolve(_criterion(policy='discount'), _evals(), 10.0, contradiction_report=_report('high', n=2))
    assert res.score_multiplier < 0.6
    assert res.contradiction_penalty > 0.5
    assert res.escalate is True
    assert res.blocked is False


def test_review_only_policy_does_not_discount_score():
    arb = ArbitrationPolicy()
    res = arb.resolve(_criterion(policy='review_only', threshold='low'), _evals(), 10.0, contradiction_report=_report('medium'))
    assert res.score_multiplier == 1.0
    assert res.escalate is True
    assert res.blocked is False
    assert res.confidence < 0.9


def test_block_if_high_blocks_criterion():
    arb = ArbitrationPolicy()
    res = arb.resolve(_criterion(policy='block_if_high', threshold='high'), _evals(), 10.0, contradiction_report=_report('high'))
    assert res.blocked is True
    assert res.score_multiplier == 0.0
    assert res.escalate is True
