from __future__ import annotations

import argparse
from pathlib import Path

from autograde.benchmarks import SyntheticBenchmarkGenerator
from autograde.cohort import CohortAnalyzer, CohortDashboardWriter, CohortSubmissionRecord
from autograde.executor import GradingExecutor
from autograde.ingestion import SubmissionIngestionPipeline
from autograde.subjects import get_subject_profile


def main() -> None:
    parser = argparse.ArgumentParser(description='Run course-scale analytics on a synthetic cohort.')
    parser.add_argument('--root', default='/mnt/data/work_autograde/course_analytics')
    parser.add_argument('--cases-per-subject', type=int, default=4)
    parser.add_argument('--output-dir', default='/mnt/data/work_autograde/course_analytics_output')
    args = parser.parse_args()

    root = Path(args.root)
    root.mkdir(parents=True, exist_ok=True)

    generator = SyntheticBenchmarkGenerator(seed=17)
    cases = generator.generate_suite(str(root), cases_per_subject=args.cases_per_subject)

    pipeline = SubmissionIngestionPipeline()
    executor = GradingExecutor()
    records: list[CohortSubmissionRecord] = []
    submissions = []

    for idx, case in enumerate(cases):
        profile = get_subject_profile(case.subject_id)
        if profile is None:
            continue
        rubric = profile.build_rubric(case.template_id, f'COURSE_{case.subject_id}_{idx}', case.case_id)
        submission = pipeline.ingest_submission(
            assignment_id=rubric.assignment_id,
            submission_path=case.submission_path,
            submission_id=case.case_id,
            student_id=f'STU_{idx:04d}',
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
    outputs = CohortDashboardWriter().write(analysis, args.output_dir)

    print(f'Total submissions: {analysis.total_submissions}')
    print(f'Average score: {analysis.average_score}')
    print(f'Review rate: {analysis.review_rate}')
    print(f'Plagiarism clusters: {len(analysis.plagiarism_clusters)}')
    print('Outputs:')
    for k, v in outputs.items():
        print(f'  {k}: {v}')


if __name__ == '__main__':
    main()
