from __future__ import annotations

from pathlib import Path

from autograde.executor import GradingExecutor
from autograde.ingestion import SubmissionIngestionPipeline
from autograde.subjects import get_subject_profile
from autograde.utils.sample_data import build_engineering_circuit_submission, build_engineering_plausible_unknown_submission


def _reset_dir(root: Path) -> None:
    if root.exists():
        for path in sorted(root.rglob('*'), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()


def test_engineering_profile_uses_completed_logic() -> None:
    profile = get_subject_profile('engineering')
    root = Path('/mnt/data/ag_v39/tests/runtime_engineering_logic_completion')
    _reset_dir(root)
    build_engineering_circuit_submission(str(root))

    submission = SubmissionIngestionPipeline().ingest_submission(
        assignment_id='EE501_C1',
        submission_path=str(root),
        submission_id='sub_eng_logic_001',
        student_id='2021EE0501',
    )
    rubric = profile.build_rubric('circuit_design', 'EE501_C1', 'Engineering Logic Completion')
    result = GradingExecutor().grade_submission(submission, rubric)

    g2 = next(cr for cr in result.criterion_results if cr.criterion_id == 'G2')
    g3 = next(cr for cr in result.criterion_results if cr.criterion_id == 'G3')
    g4 = next(cr for cr in result.criterion_results if cr.criterion_id == 'G4')

    ids2 = {er.evaluator_id for er in g2.evaluator_results}
    ids3 = {er.evaluator_id for er in g3.evaluator_results}
    ids4 = {er.evaluator_id for er in g4.evaluator_results}

    assert 'topology_constraint_satisfaction' in ids2
    assert 'alternative_design_plausibility' in ids2
    assert 'behavioral_metric_alignment' in ids3
    assert 'design_report_alignment' in ids4
    assert result.final_score > 0


def test_engineering_unknown_but_plausible_design_not_zeroed() -> None:
    profile = get_subject_profile('engineering')
    root = Path('/mnt/data/ag_v39/tests/runtime_engineering_logic_alt')
    _reset_dir(root)
    build_engineering_plausible_unknown_submission(str(root))
    submission = SubmissionIngestionPipeline().ingest_submission(
        assignment_id='EE501_C2',
        submission_path=str(root),
        submission_id='sub_eng_logic_002',
        student_id='2021EE0502',
    )
    rubric = profile.build_rubric('circuit_design', 'EE501_C2', 'Engineering Logic Alt')
    result = GradingExecutor().grade_submission(submission, rubric)
    g2 = next(cr for cr in result.criterion_results if cr.criterion_id == 'G2')
    assert g2.score > 0
