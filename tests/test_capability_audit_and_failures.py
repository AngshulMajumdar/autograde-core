from __future__ import annotations

from autograde.executor.failure_detection import detect_submission_failures
from autograde.executor.explanation import build_score_explanation
from autograde.models import CriterionResult, Submission
from scripts.system_audit import run_audit


def test_system_audit_has_expected_buckets() -> None:
    summary = run_audit()
    assert "capabilities" in summary
    assert summary["capabilities"]["text"] == "strong"
    assert "cad" in summary["unsupported"]


def test_failure_detection_and_explanation() -> None:
    submission = Submission(submission_id="s1", assignment_id="a1", student_id="u1", submitted_at=None)
    failures = detect_submission_failures(submission)
    assert failures
    assert failures[0]["type"] == "empty_submission"

    result = CriterionResult(
        criterion_id="C1",
        score=7.5,
        max_score=10.0,
        confidence=0.4,
        rationale="test",
        evidence_ids=["ev1"],
        flags=[{"type": "x"}],
        status="partially_graded",
        capability_status="partial",
        support_status="partial",
        coverage_status="covered",
        evidence_strength=0.8,
        effective_weight=0.2,
    )
    explanation = build_score_explanation(result)
    assert explanation["criterion_id"] == "C1"
    assert explanation["final_contribution_estimate"] > 0
