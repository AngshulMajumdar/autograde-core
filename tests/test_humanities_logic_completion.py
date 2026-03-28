from __future__ import annotations

from pathlib import Path

from autograde.executor import GradingExecutor
from autograde.ingestion import SubmissionIngestionPipeline
from autograde.subjects import get_subject_profile
from autograde.utils.sample_data import build_humanities_essay_submission


def _reset_dir(root: Path) -> None:
    if root.exists():
        for path in sorted(root.rglob('*'), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()


def test_humanities_profile_uses_completed_logic() -> None:
    profile = get_subject_profile('humanities')
    root = Path('/mnt/data/ag_v36/tests/runtime_humanities_logic_completion')
    _reset_dir(root)
    build_humanities_essay_submission(str(root))

    submission = SubmissionIngestionPipeline().ingest_submission(
        assignment_id='HU201_E2',
        submission_path=str(root),
        submission_id='sub_hum_logic_001',
        student_id='2021HU0201',
    )
    rubric = profile.build_rubric('essay', 'HU201_E2', 'Humanities Logic Completion')
    result = GradingExecutor().grade_submission(submission, rubric)

    e1 = next(cr for cr in result.criterion_results if cr.criterion_id == 'E1')
    e2 = next(cr for cr in result.criterion_results if cr.criterion_id == 'E2')
    e3 = next(cr for cr in result.criterion_results if cr.criterion_id == 'E3')
    e4 = next(cr for cr in result.criterion_results if cr.criterion_id == 'E4')

    ids1 = {er.evaluator_id for er in e1.evaluator_results}
    ids2 = {er.evaluator_id for er in e2.evaluator_results}
    ids3 = {er.evaluator_id for er in e3.evaluator_results}
    ids4 = {er.evaluator_id for er in e4.evaluator_results}

    assert 'prompt_relevance' in ids1
    assert 'counterargument_awareness' in ids2
    assert 'interpretive_depth' in ids2
    assert 'source_integration' in ids3
    assert 'discourse_structure' in ids4
    assert result.final_score > 0
