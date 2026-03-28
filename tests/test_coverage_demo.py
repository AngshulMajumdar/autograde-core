from __future__ import annotations

from pathlib import Path

from autograde.executor import GradingExecutor
from autograde.ingestion import SubmissionIngestionPipeline
from autograde.outputs import ReportFormatter
from autograde.rubric import Criterion, CriterionAspect, Rubric, ScoringPolicy
from autograde.utils.sample_data import build_sample_submission


def build_rubric() -> Rubric:
    return Rubric(
        assignment_id='CS301_A7',
        assignment_title='Coverage Logic Test',
        required_artifacts=['report', 'source_code', 'spreadsheet'],
        criteria=[
            Criterion(
                criterion_id='C1',
                name='Experimental reporting',
                description='Assess whether the submission presents and interprets results completely.',
                max_score=20,
                weight=0.5,
                required_modalities=['text', 'table'],
                evaluation_dimensions=['clarity', 'completeness'],
                artifact_scope=['report', 'spreadsheet'],
                scoring_policy=ScoringPolicy(mode='analytic_bands'),
                aspects=[
                    CriterionAspect(
                        aspect_id='results_present',
                        description='Results table exists.',
                        required=True,
                        modalities=['table'],
                        evidence_types=['csv_table'],
                    ),
                    CriterionAspect(
                        aspect_id='interpretation',
                        description='Results are interpreted in report text.',
                        required=True,
                        modalities=['text'],
                        evidence_types=['paragraph'],
                    ),
                    CriterionAspect(
                        aspect_id='baseline_comparison',
                        description='Baseline comparison is present.',
                        required=True,
                        tags=['baseline'],
                    ),
                ],
            ),
            Criterion(
                criterion_id='C2',
                name='Method and implementation',
                description='Assess whether the method and code are both present.',
                max_score=20,
                weight=0.5,
                required_modalities=['text', 'code'],
                evaluation_dimensions=['correctness', 'consistency'],
                evaluator_hints=['code_quality'],
                artifact_scope=['report', 'source_code'],
                scoring_policy=ScoringPolicy(mode='weighted_average'),
                aspects=[
                    CriterionAspect(
                        aspect_id='method_description',
                        description='Method description appears in report.',
                        required=True,
                        modalities=['text'],
                        evidence_types=['paragraph'],
                    ),
                    CriterionAspect(
                        aspect_id='implementation_present',
                        description='Implementation code is present.',
                        required=True,
                        modalities=['code'],
                        evidence_types=['function'],
                    ),
                ],
            ),
        ],
        normalize_to=100.0,
    )


def _reset_dir(root: Path) -> None:
    if root.exists():
        for path in sorted(root.rglob('*'), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()


def main() -> None:
    root = Path('/mnt/data/ag_v11/tests/runtime_coverage_submission')
    _reset_dir(root)
    build_sample_submission(str(root))

    pipeline = SubmissionIngestionPipeline()
    submission = pipeline.ingest_submission(
        assignment_id='CS301_A7',
        submission_path=str(root),
        submission_id='sub_cov_001',
        student_id='2021CS7777',
    )

    result = GradingExecutor().grade_submission(submission, build_rubric())
    print(ReportFormatter.student_feedback(result))

    c1 = next(cr for cr in result.criterion_results if cr.criterion_id == 'C1')
    c2 = next(cr for cr in result.criterion_results if cr.criterion_id == 'C2')

    assert c1.coverage_status == 'missing_required', c1
    assert any(item['aspect_id'] == 'baseline_comparison' and item['status'] == 'missing' for item in c1.coverage_results), c1.coverage_results
    assert c1.score <= 12.0, c1  # 60% cap from coverage rules on a 20-point criterion

    assert c2.coverage_status == 'covered', c2.coverage_results
    assert len(c2.coverage_results) == 2
    assert c2.score > 0
    assert result.final_score > 0


if __name__ == '__main__':
    main()
