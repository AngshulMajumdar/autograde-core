from pathlib import Path

from autograde.ingestion import SubmissionIngestionPipeline
from autograde.subjects.registry import get_subject_profile
from autograde.executor import GradingExecutor
from autograde.utils.sample_data import build_mathematics_handwritten_like_submission


def test_mathematics_handwritten_like_submission_runs(tmp_path: Path):
    root = tmp_path / "math_handwritten"
    build_mathematics_handwritten_like_submission(str(root))
    pipeline = SubmissionIngestionPipeline()
    submission = pipeline.ingest_submission(
        assignment_id="MATH_HW",
        submission_path=str(root),
        submission_id="sub_math_hand",
        student_id="s1",
    )
    assert any(e.modality in {"text", "equation", "image"} for e in submission.evidence)

    profile = get_subject_profile("mathematics")
    rubric = profile.build_rubric("proof", assignment_id="MATH_HW", assignment_title="Handwritten Proof")
    result = GradingExecutor().grade_submission(submission, rubric)
    assert result.final_score >= 0.0
    assert len(result.criterion_results) == 4
