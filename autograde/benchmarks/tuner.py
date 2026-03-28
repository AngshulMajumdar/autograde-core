from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean
from typing import Dict, Iterable, List

from .runner import BenchmarkRunResult


@dataclass(slots=True)
class SubjectCalibration:
    subject_id: str
    case_count: int
    pass_rate: float
    avg_score: float
    avg_confidence: float
    review_rate: float
    escalation_rate: float
    partial_rate: float
    suggested_low_confidence_threshold: float
    suggested_review_bias: str
    notes: List[str] = field(default_factory=list)


@dataclass(slots=True)
class CalibrationReport:
    overall_pass_rate: float
    overall_review_rate: float
    subjects: Dict[str, SubjectCalibration]

    def to_text(self) -> str:
        lines = [
            '==== AUTOGRADE BENCHMARK CALIBRATION REPORT ====',
            f'Overall pass rate: {self.overall_pass_rate:.2%}',
            f'Overall review rate: {self.overall_review_rate:.2%}',
            '',
            'By subject:'
        ]
        for subject_id, cal in sorted(self.subjects.items()):
            lines.append(
                f"- {subject_id}: pass_rate={cal.pass_rate:.2%}, review_rate={cal.review_rate:.2%}, avg_confidence={cal.avg_confidence:.3f}, suggested_low_conf_threshold={cal.suggested_low_confidence_threshold:.2f}, review_bias={cal.suggested_review_bias}"
            )
            for note in cal.notes:
                lines.append(f"    * {note}")
        return '\n'.join(lines)


class BenchmarkTuner:
    """Calibrates conservative thresholds from benchmark outcomes.

    This does not rewrite the core engine automatically. It produces defensible,
    subject-specific suggestions that can be applied later.
    """

    def calibrate(self, results: Iterable[BenchmarkRunResult]) -> CalibrationReport:
        results = list(results)
        if not results:
            return CalibrationReport(0.0, 0.0, {})

        by_subject: Dict[str, List[BenchmarkRunResult]] = {}
        for result in results:
            by_subject.setdefault(result.subject_id, []).append(result)

        subject_reports: Dict[str, SubjectCalibration] = {}
        for subject_id, subject_results in by_subject.items():
            subject_reports[subject_id] = self._calibrate_subject(subject_id, subject_results)

        overall_pass_rate = sum(1 for r in results if r.passed) / len(results)
        overall_review_rate = sum(1 for r in results if r.review_required) / len(results)
        return CalibrationReport(
            overall_pass_rate=overall_pass_rate,
            overall_review_rate=overall_review_rate,
            subjects=subject_reports,
        )

    def _calibrate_subject(self, subject_id: str, results: List[BenchmarkRunResult]) -> SubjectCalibration:
        case_count = len(results)
        pass_rate = sum(1 for r in results if r.passed) / case_count
        avg_score = mean(r.score for r in results)
        avg_conf = mean(r.average_confidence for r in results)
        review_rate = sum(1 for r in results if r.review_required) / case_count
        escalation_rate = sum(1 for r in results if 'escalated' in r.statuses or 'unsupported_needs_review' in r.statuses for _ in [0]) / case_count
        partial_rate = sum(1 for r in results if 'partially_graded' in r.statuses for _ in [0]) / case_count

        suggested = 0.65
        bias = 'balanced'
        notes: List[str] = []

        # Over-reviewing: lower threshold modestly.
        if review_rate > 0.55 and avg_conf > 0.55:
            suggested = 0.58
            bias = 'less_review'
            notes.append('Review rate is high relative to average confidence; lower the low-confidence threshold slightly.')
        elif review_rate < 0.15 and avg_conf < 0.62:
            suggested = 0.70
            bias = 'more_review'
            notes.append('Review rate is low while confidence is also low; increase review conservatism.')

        # Subject-specific conservative defaults.
        if subject_id in {'humanities', 'mathematics'}:
            suggested = max(suggested, 0.67)
            if bias == 'balanced':
                bias = 'more_review'
            notes.append('Subject contains high-subjectivity or higher-rigor reasoning; retain a more conservative review posture.')
        elif subject_id == 'programming' and review_rate > 0.45 and partial_rate > 0.25:
            suggested = min(suggested, 0.60)
            bias = 'less_review'
            notes.append('Programming profile is likely over-escalating probeable but incomplete submissions.')
        elif subject_id == 'engineering' and escalation_rate > 0.30:
            suggested = max(suggested, 0.68)
            bias = 'more_review'
            notes.append('Engineering profile sees many plausible-but-unknown designs; keep conservative escalation.')

        if pass_rate < 0.45:
            notes.append('Pass rate on benchmark expectations is low; evaluator or profile tuning is likely needed beyond threshold adjustment.')
        if partial_rate > 0.40:
            notes.append('Partial grading is common; review coverage caps and required-aspect settings for this profile.')

        return SubjectCalibration(
            subject_id=subject_id,
            case_count=case_count,
            pass_rate=pass_rate,
            avg_score=avg_score,
            avg_confidence=avg_conf,
            review_rate=review_rate,
            escalation_rate=escalation_rate,
            partial_rate=partial_rate,
            suggested_low_confidence_threshold=round(suggested, 2),
            suggested_review_bias=bias,
            notes=notes,
        )



def build_subject_tunings(report: CalibrationReport) -> dict[str, dict[str, object]]:
    """Serialize calibration suggestions into a simple mapping that can be applied by profiles/runners."""
    tuned: dict[str, dict[str, object]] = {}
    for subject_id, cal in report.subjects.items():
        tuned[subject_id] = {
            "low_confidence_threshold": cal.suggested_low_confidence_threshold,
            "review_bias": cal.suggested_review_bias,
            "notes": list(cal.notes),
        }
    return tuned
