from __future__ import annotations

from pathlib import Path

from autograde.executor import GradingExecutor
from autograde.ingestion import SubmissionIngestionPipeline
from autograde.outputs import ReportFormatter
from autograde.subjects import get_subject_profile
from autograde.utils.sample_data import build_mathematics_proof_submission


def _reset_dir(root: Path) -> None:
    if root.exists():
        for path in sorted(root.rglob('*'), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()


def main() -> None:
    profile = get_subject_profile('mathematics')
    assert profile is not None
    assert set(profile.available_templates()) == {'proof', 'derivation'}

    root = Path('/mnt/data/ag_v16/tests/runtime_mathematics')
    _reset_dir(root)
    build_mathematics_proof_submission(str(root))

    pipeline = SubmissionIngestionPipeline()
    submission = pipeline.ingest_submission(
        assignment_id='MA101_P1',
        submission_path=str(root),
        submission_id='sub_math_001',
        student_id='2021MA0001',
    )
    rubric = profile.build_rubric('proof', 'MA101_P1', 'Mathematics Proof Demo')
    result = GradingExecutor().grade_submission(submission, rubric)
    print(ReportFormatter.student_feedback(result))

    assert len(rubric.criteria) == 4
    assert result.final_score > 0
    m2 = next(cr for cr in result.criterion_results if cr.criterion_id == 'M2')
    assert any(er.evaluator_id == 'subjective_answer_quality' for er in m2.evaluator_results)
    assert any(er.evaluator_id == 'argumentation' for er in m2.evaluator_results)


if __name__ == '__main__':
    main()
