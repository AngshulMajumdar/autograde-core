from __future__ import annotations

from pathlib import Path

from autograde.executor import GradingExecutor
from autograde.ingestion import SubmissionIngestionPipeline
from autograde.outputs import ReportFormatter
from autograde.subjects import get_subject_profile
from autograde.utils.sample_data import (
    build_engineering_circuit_submission,
    build_engineering_plausible_unknown_submission,
)


def _reset_dir(root: Path) -> None:
    if root.exists():
        for path in sorted(root.rglob('*'), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()


def main() -> None:
    profile = get_subject_profile('engineering')
    assert profile is not None
    assert profile.available_templates() == ['circuit_design']

    pipeline = SubmissionIngestionPipeline()
    executor = GradingExecutor()

    known_root = Path('/mnt/data/ag_v15/tests/runtime_engineering_known')
    _reset_dir(known_root)
    build_engineering_circuit_submission(str(known_root))
    sub_known = pipeline.ingest_submission(
        assignment_id='EE401_C1',
        submission_path=str(known_root),
        submission_id='sub_eng_001',
        student_id='2021EE0001',
    )
    rubric = profile.build_rubric('circuit_design', 'EE401_C1', 'Engineering Circuit Demo')
    result_known = executor.grade_submission(sub_known, rubric)
    print(ReportFormatter.student_feedback(result_known))
    assert len(rubric.criteria) == 4
    g2 = next(cr for cr in result_known.criterion_results if cr.criterion_id == 'G2')
    assert any(er.evaluator_id == 'design_functional_plausibility' for er in g2.evaluator_results)
    assert result_known.final_score > 0

    alt_root = Path('/mnt/data/ag_v15/tests/runtime_engineering_alt')
    _reset_dir(alt_root)
    build_engineering_plausible_unknown_submission(str(alt_root))
    sub_alt = pipeline.ingest_submission(
        assignment_id='EE401_C2',
        submission_path=str(alt_root),
        submission_id='sub_eng_002',
        student_id='2021EE0002',
    )
    result_alt = executor.grade_submission(sub_alt, rubric)
    print(ReportFormatter.student_feedback(result_alt))
    g2_alt = next(cr for cr in result_alt.criterion_results if cr.criterion_id == 'G2')
    # The alternative design should not be zeroed out simply because it differs from a single reference family.
    assert g2_alt.score > 0


if __name__ == '__main__':
    main()
