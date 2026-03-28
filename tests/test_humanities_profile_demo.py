from __future__ import annotations

from pathlib import Path

from autograde.executor import GradingExecutor
from autograde.ingestion import SubmissionIngestionPipeline
from autograde.outputs import ReportFormatter
from autograde.subjects import get_subject_profile
from autograde.utils.sample_data import (
    build_humanities_essay_submission,
    build_humanities_short_answer_submission,
)


def _reset_dir(root: Path) -> None:
    if root.exists():
        for path in sorted(root.rglob('*'), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()


def main() -> None:
    profile = get_subject_profile('humanities')
    assert profile is not None
    assert set(profile.available_templates()) == {'short_answer', 'essay'}

    pipeline = SubmissionIngestionPipeline()
    executor = GradingExecutor()

    short_root = Path('/mnt/data/ag_v14/tests/runtime_humanities_short_answer')
    _reset_dir(short_root)
    build_humanities_short_answer_submission(str(short_root))
    short_submission = pipeline.ingest_submission(
        assignment_id='HU101_S1',
        submission_path=str(short_root),
        submission_id='sub_hum_short_001',
        student_id='2021HU0001',
    )
    short_rubric = profile.build_rubric('short_answer', 'HU101_S1', 'Humanities Short Answer Demo')
    short_result = executor.grade_submission(short_submission, short_rubric)
    print(ReportFormatter.student_feedback(short_result))
    assert len(short_rubric.criteria) == 3
    assert short_result.final_score > 0
    h1 = next(cr for cr in short_result.criterion_results if cr.criterion_id == 'H1')
    assert any(er.evaluator_id == 'subjective_answer_quality' for er in h1.evaluator_results)
    assert h1.coverage_results

    essay_root = Path('/mnt/data/ag_v14/tests/runtime_humanities_essay')
    _reset_dir(essay_root)
    build_humanities_essay_submission(str(essay_root))
    essay_submission = pipeline.ingest_submission(
        assignment_id='HU101_E1',
        submission_path=str(essay_root),
        submission_id='sub_hum_essay_001',
        student_id='2021HU0002',
    )
    essay_rubric = profile.build_rubric('essay', 'HU101_E1', 'Humanities Essay Demo')
    essay_result = executor.grade_submission(essay_submission, essay_rubric)
    print(ReportFormatter.student_feedback(essay_result))
    assert len(essay_rubric.criteria) == 4
    assert essay_result.final_score > short_result.final_score * 0.5
    e3 = next(cr for cr in essay_result.criterion_results if cr.criterion_id == 'E3')
    assert any(er.evaluator_id == 'citation_integrity' for er in e3.evaluator_results)
    assert any(er.evaluator_id == 'subjective_answer_quality' for er in e3.evaluator_results)


if __name__ == '__main__':
    main()
