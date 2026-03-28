from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean
from typing import Iterable

from autograde.executor import GradingExecutor
from autograde.ingestion import SubmissionIngestionPipeline
from autograde.subjects import get_subject_profile
from autograde.subjects.tuning import SubjectTuning, tuning_from_mapping

from .generator import BenchmarkCase


@dataclass(slots=True)
class BenchmarkRunResult:
    case_id: str
    subject_id: str
    template_id: str
    score: float
    average_confidence: float
    review_required: bool
    statuses: list[str] = field(default_factory=list)
    passed: bool = False
    notes: str = ''


class BenchmarkRunner:
    def __init__(self, subject_tunings: dict[str, dict[str, object]] | None = None) -> None:
        self.pipeline = SubmissionIngestionPipeline()
        self.executor = GradingExecutor()
        self.subject_tunings = subject_tunings or {}

    def run_case(self, case: BenchmarkCase) -> BenchmarkRunResult:
        profile = get_subject_profile(case.subject_id)
        if profile is None:
            raise ValueError(f'Unknown subject profile: {case.subject_id}')
        rubric = profile.build_rubric(case.template_id, f'BENCH_{case.case_id}', f'Benchmark {case.case_id}')
        tuning_map = self.subject_tunings.get(case.subject_id)
        if tuning_map:
            rubric = tuning_from_mapping(case.subject_id, tuning_map).apply(rubric)
        submission = self.pipeline.ingest_submission(
            assignment_id=rubric.assignment_id,
            submission_path=case.submission_path,
            submission_id=case.case_id,
            student_id=case.case_id,
        )
        result = self.executor.grade_submission(submission, rubric)
        statuses = [cr.status for cr in result.criterion_results]
        avg_conf = mean([cr.confidence for cr in result.criterion_results]) if result.criterion_results else 0.0
        review_required = bool(result.review_bundles)
        score_ok = case.expected_min_score <= result.final_score <= case.expected_max_score
        review_ok = review_required == case.expected_review
        statuses_ok = True
        if case.expected_statuses:
            statuses_ok = any(s in statuses for s in case.expected_statuses)
        return BenchmarkRunResult(
            case_id=case.case_id,
            subject_id=case.subject_id,
            template_id=case.template_id,
            score=result.final_score,
            average_confidence=round(avg_conf, 3),
            review_required=review_required,
            statuses=statuses,
            passed=score_ok and review_ok and statuses_ok,
            notes=case.notes,
        )

    def run_suite(self, cases: Iterable[BenchmarkCase]) -> list[BenchmarkRunResult]:
        return [self.run_case(case) for case in cases]
