from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median

from autograde.benchmarks.generator import SyntheticBenchmarkGenerator
from autograde.benchmarks.runner import BenchmarkRunner


def simulate(output_dir: str, submissions: int = 200, seed: int = 17) -> dict[str, object]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    cases_per_subject = max(1, submissions // 5)
    generator = SyntheticBenchmarkGenerator(seed=seed)
    cases = generator.generate_suite(str(out / 'cases'), cases_per_subject=cases_per_subject)
    runner = BenchmarkRunner()
    results = runner.run_suite(cases)
    scores = [r.score for r in results]
    confidences = [r.average_confidence for r in results]
    review_rate = sum(1 for r in results if r.review_required) / max(1, len(results))
    by_subject: dict[str, dict[str, object]] = {}
    for subject in sorted({r.subject_id for r in results}):
        subset = [r for r in results if r.subject_id == subject]
        by_subject[subject] = {
            'count': len(subset),
            'avg_score': round(mean([r.score for r in subset]), 2),
            'avg_confidence': round(mean([r.average_confidence for r in subset]), 3),
            'review_rate': round(sum(1 for r in subset if r.review_required) / max(1, len(subset)), 3),
            'pass_rate': round(sum(1 for r in subset if r.passed) / max(1, len(subset)), 3),
            'status_counts': dict(Counter(s for r in subset for s in r.statuses)),
        }
    review_heavy = sorted([r.case_id for r in results if r.review_required])
    low_confidence = sorted([r.case_id for r in results if r.average_confidence < 0.5])
    summary = {
        'requested_submissions': submissions,
        'generated_cases': len(results),
        'avg_score': round(mean(scores), 2) if scores else 0.0,
        'median_score': round(median(scores), 2) if scores else 0.0,
        'avg_confidence': round(mean(confidences), 3) if confidences else 0.0,
        'review_rate': round(review_rate, 3),
        'pass_rate': round(sum(1 for r in results if r.passed) / max(1, len(results)), 3),
        'subjects': by_subject,
        'review_cases': review_heavy,
        'low_confidence_cases': low_confidence,
    }
    (out / 'course_simulation_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    lines = [
        f"Generated cases: {summary['generated_cases']}",
        f"Average score: {summary['avg_score']}",
        f"Median score: {summary['median_score']}",
        f"Average confidence: {summary['avg_confidence']}",
        f"Review rate: {summary['review_rate']}",
        f"Pass rate: {summary['pass_rate']}",
        '',
        'Per-subject breakdown:',
    ]
    for subject, info in by_subject.items():
        lines.append(f"- {subject}: count={info['count']} avg_score={info['avg_score']} avg_confidence={info['avg_confidence']} review_rate={info['review_rate']} pass_rate={info['pass_rate']}")
    (out / 'course_simulation_report.txt').write_text('\n'.join(lines), encoding='utf-8')
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', default='course_simulation_out')
    parser.add_argument('--submissions', type=int, default=200)
    parser.add_argument('--seed', type=int, default=17)
    args = parser.parse_args()
    summary = simulate(args.output_dir, submissions=args.submissions, seed=args.seed)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
