from autograde.models import CriterionResult, GradingResult
from autograde.outputs.reporting import ReportFormatter


def test_llm_feedback_demo():
    result = GradingResult(
        submission_id='sub1',
        criterion_results=[
            CriterionResult('C1', 8.0, 10.0, 0.81, 'Strong core answer with minor evidence gaps.'),
            CriterionResult('C2', 6.0, 10.0, 0.55, 'Some claims are weakly supported.', status='partially_graded'),
        ],
        final_score=70.0,
        max_score=100.0,
        review_bundles=[{'criterion_id': 'C2', 'reason': 'low_confidence'}],
    )
    text = ReportFormatter.student_feedback(result, use_llm=True)
    assert 'Strengths:' in text
    assert 'Weaknesses:' in text
    assert 'Suggestions:' in text
