from __future__ import annotations

from pathlib import Path

from autograde.executor import GradingExecutor
from autograde.ingestion import SubmissionIngestionPipeline
from autograde.outputs import ReportFormatter
from autograde.subjects import get_subject_profile
from autograde.utils.sample_data import build_hardcoded_but_probeable_submission


def _reset_dir(root: Path) -> None:
    if root.exists():
        for path in sorted(root.rglob('*'), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()


def main() -> None:
    profile = get_subject_profile('programming')
    assert profile is not None
    assert 'programming_project' in profile.available_templates()

    root = Path('/mnt/data/ag_v13/tests/runtime_programming_profile_submission')
    _reset_dir(root)
    build_hardcoded_but_probeable_submission(str(root))

    pipeline = SubmissionIngestionPipeline()
    submission = pipeline.ingest_submission(
        assignment_id='CS999_P1',
        submission_path=str(root),
        submission_id='sub_prof_001',
        student_id='2021CS4242',
    )

    rubric = profile.build_rubric(
        template_id='programming_project',
        assignment_id='CS999_P1',
        assignment_title='Programming Profile Demo',
    )

    result = GradingExecutor().grade_submission(submission, rubric)
    print(profile.metadata)
    print(ReportFormatter.student_feedback(result))

    assert len(rubric.criteria) == 5
    assert {c.criterion_id for c in rubric.criteria} == {'P1', 'P2', 'P3', 'P4', 'P5'}
    assert result.final_score > 0

    p1 = next(cr for cr in result.criterion_results if cr.criterion_id == 'P1')
    p3 = next(cr for cr in result.criterion_results if cr.criterion_id == 'P3')
    p4 = next(cr for cr in result.criterion_results if cr.criterion_id == 'P4')

    assert p1.score > 0
    assert any(er.evaluator_id == 'behavioral_correctness' for er in p1.evaluator_results)
    assert any(er.evaluator_id == 'implementation_report_alignment' for er in p3.evaluator_results)
    assert p4.coverage_results, p4


if __name__ == '__main__':
    main()
