from __future__ import annotations

from pathlib import Path

from autograde.benchmarks import BenchmarkReporter, BenchmarkRunner, SyntheticBenchmarkGenerator


def main() -> None:
    base = Path('/mnt/data/autograde_synthetic_benchmarks_report')
    cases = SyntheticBenchmarkGenerator(seed=29).generate_suite(str(base), cases_per_subject=10)
    results = BenchmarkRunner().run_suite(cases)
    reporter = BenchmarkReporter()
    report = reporter.to_text(results)
    print(report)
    (base / 'benchmark_report.txt').parent.mkdir(parents=True, exist_ok=True)
    (base / 'benchmark_report.txt').write_text(report, encoding='utf-8')


if __name__ == '__main__':
    main()
