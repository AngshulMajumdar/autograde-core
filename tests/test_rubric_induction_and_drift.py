from __future__ import annotations

from autograde.rubric.induction import PastCase, induce_rubric_from_past_cases
from autograde.rubric.drift import RubricDriftDetector


def test_rubric_induction_llm_plus_deterministic() -> None:
    cases = [
        PastCase('Correct implementation, weak explanation, missing comparison.', 'Implementation is mostly correct, but the analysis and comparison with baseline are missing.', 72),
        PastCase('Strong explanation and analysis, but implementation has correctness errors.', 'The writeup is clear, but the code behavior is not correct on important test cases.', 61),
        PastCase('Excellent correctness, good explanation, reasonable analysis.', 'Strong submission overall. Correct solution with clear reasoning and adequate result discussion.', 88),
    ]
    rubric = induce_rubric_from_past_cases(cases, subject_profile='programming')
    assert rubric.assignment_id == 'induced_programming'
    assert 3 <= len(rubric.criteria) <= 6
    total_weight = sum(c.weight for c in rubric.criteria)
    assert 0.95 <= total_weight <= 1.05
    assert all(c.evaluator_hints for c in rubric.criteria)


def test_rubric_drift_detection() -> None:
    baseline_cases = [
        PastCase('Correct code, weak explanation.', 'Correctness is good but explanation is weak.', 70),
        PastCase('Good code and decent analysis.', 'Strong correctness and some analysis.', 82),
    ]
    recent_cases = [
        PastCase('Correct code, strong results discussion.', 'Correctness is strong and result interpretation matters a lot.', 84),
        PastCase('Correct code, poor analysis.', 'Missing analysis and interpretation of outcomes.', 68),
    ]
    baseline = induce_rubric_from_past_cases(baseline_cases, 'programming')
    detector = RubricDriftDetector()
    report = detector.induce_and_compare(baseline, recent_cases, 'programming')
    assert report.subject_profile == 'programming'
    assert report.old_criteria_count >= 1
    assert report.new_criteria_count >= 1
    assert isinstance(report.significant_drift, bool)
