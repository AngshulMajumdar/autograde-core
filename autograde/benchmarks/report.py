from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from statistics import mean

from .runner import BenchmarkRunResult


@dataclass(slots=True)
class BenchmarkSummary:
    total_cases: int
    passed_cases: int
    average_score: float
    average_confidence: float
    review_rate: float
    by_subject: dict[str, dict[str, float]]


class BenchmarkReporter:
    def summarize(self, results: list[BenchmarkRunResult]) -> BenchmarkSummary:
        if not results:
            return BenchmarkSummary(0, 0, 0.0, 0.0, 0.0, {})
        by_subject_raw: dict[str, list[BenchmarkRunResult]] = defaultdict(list)
        for r in results:
            by_subject_raw[r.subject_id].append(r)
        by_subject = {}
        for subject, subject_results in by_subject_raw.items():
            by_subject[subject] = {
                'count': float(len(subject_results)),
                'pass_rate': sum(1 for r in subject_results if r.passed) / len(subject_results),
                'avg_score': mean(r.score for r in subject_results),
                'avg_confidence': mean(r.average_confidence for r in subject_results),
                'review_rate': sum(1 for r in subject_results if r.review_required) / len(subject_results),
            }
        return BenchmarkSummary(
            total_cases=len(results),
            passed_cases=sum(1 for r in results if r.passed),
            average_score=mean(r.score for r in results),
            average_confidence=mean(r.average_confidence for r in results),
            review_rate=sum(1 for r in results if r.review_required) / len(results),
            by_subject=by_subject,
        )

    def to_text(self, results: list[BenchmarkRunResult]) -> str:
        summary = self.summarize(results)
        lines = [
            '==== AUTOGRADE SYNTHETIC BENCHMARK REPORT ====',
            f'Total cases: {summary.total_cases}',
            f'Passed cases: {summary.passed_cases}',
            f'Average score: {summary.average_score:.2f}',
            f'Average confidence: {summary.average_confidence:.3f}',
            f'Review rate: {summary.review_rate:.2%}',
            '',
            'By subject:'
        ]
        for subject, stats in sorted(summary.by_subject.items()):
            lines.append(
                f"- {subject}: pass_rate={stats['pass_rate']:.2%}, avg_score={stats['avg_score']:.2f}, avg_confidence={stats['avg_confidence']:.3f}, review_rate={stats['review_rate']:.2%}"
            )
        failures = [r for r in results if not r.passed]
        if failures:
            lines.extend(['', 'Failures:'])
            for fail in failures[:20]:
                lines.append(
                    f"- {fail.case_id} ({fail.subject_id}/{fail.template_id}): score={fail.score:.2f}, review={fail.review_required}, statuses={fail.statuses}"
                )
        return '\n'.join(lines)
