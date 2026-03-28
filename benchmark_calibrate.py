from __future__ import annotations

from pathlib import Path

from autograde.benchmarks import BenchmarkReporter, BenchmarkRunner, BenchmarkTuner, SyntheticBenchmarkGenerator


def main() -> None:
    base = Path('/mnt/data/autograde_synthetic_benchmarks_calibration')
    base.mkdir(parents=True, exist_ok=True)
    cases = SyntheticBenchmarkGenerator(seed=41).generate_suite(str(base / 'cases'), cases_per_subject=12)
    results = BenchmarkRunner().run_suite(cases)
    reporter = BenchmarkReporter()
    tuner = BenchmarkTuner()
    bench_text = reporter.to_text(results)
    calibration_text = tuner.calibrate(results).to_text()
    print(bench_text)
    print()
    print(calibration_text)
    (base / 'benchmark_report.txt').write_text(bench_text, encoding='utf-8')
    (base / 'calibration_report.txt').write_text(calibration_text, encoding='utf-8')


if __name__ == '__main__':
    main()
