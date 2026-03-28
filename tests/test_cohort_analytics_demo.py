from __future__ import annotations

from pathlib import Path

from autograde.benchmarks import SyntheticBenchmarkGenerator
from autograde.cohort import CohortAnalyzer, CohortDashboardWriter, CohortSubmissionRecord
from autograde.executor import GradingExecutor
from autograde.ingestion import SubmissionIngestionPipeline
from autograde.subjects import get_subject_profile


def main() -> None:
    base = Path('/mnt/data/work_autograde/tests/runtime_cohort_analytics')
    base.mkdir(parents=True, exist_ok=True)
    gen = SyntheticBenchmarkGenerator(seed=23)
    cases = gen.generate_suite(str(base), cases_per_subject=2)

    pipeline = SubmissionIngestionPipeline()
    executor = GradingExecutor()
    records = []
    submissions = []

    for idx, case in enumerate(cases):
        profile = get_subject_profile(case.subject_id)
        rubric = profile.build_rubric(case.template_id, f'ANALYTICS_{idx}', case.case_id)
        submission = pipeline.ingest_submission(
            assignment_id=rubric.assignment_id,
            submission_path=case.submission_path,
            submission_id=case.case_id,
            student_id=f'S{idx:03d}',
        )
        result = executor.grade_submission(submission, rubric)
        submissions.append(submission)
        records.append(CohortSubmissionRecord(
            submission_id=submission.submission_id,
            student_id=submission.student_id,
            subject_id=case.subject_id,
            template_id=case.template_id,
            grading_result=result,
        ))

    cohort_flags = executor.grade_cohort_similarity(submissions)
    analysis = CohortAnalyzer().analyze(records, cohort_flags=cohort_flags)

    assert analysis.total_submissions == len(records)
    assert analysis.average_score >= 0.0
    assert analysis.review_rate >= 0.0
    assert analysis.priority_review_counts is not None
    assert set(analysis.priority_review_counts).issuperset({'critical', 'high', 'medium', 'low'})
    assert analysis.subject_breakdown

    out = Path('/mnt/data/work_autograde/tests/runtime_cohort_analytics_output')
    outputs = CohortDashboardWriter().write(analysis, str(out))
    for path in outputs.values():
        assert Path(path).exists()


if __name__ == '__main__':
    main()


def test_cohort_analytics_demo():
    main()
