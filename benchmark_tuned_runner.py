from __future__ import annotations

from pathlib import Path

from autograde.benchmarks.generator import SyntheticBenchmarkGenerator
from autograde.benchmarks.report import BenchmarkReportBuilder
from autograde.benchmarks.runner import BenchmarkRunner
from autograde.benchmarks.tuner import BenchmarkTuner, build_subject_tunings


def main() -> None:
    root = Path('benchmarks_runtime_tuned')
    generator = SyntheticBenchmarkGenerator(seed=17)
    cases = generator.generate_suite(str(root), cases_per_subject=4)

    base_runner = BenchmarkRunner()
    base_results = base_runner.run_suite(cases)
    report = BenchmarkReportBuilder().build(base_results)
    print(report.to_text())

    calibration = BenchmarkTuner().calibrate(base_results)
    tuned_runner = BenchmarkRunner(subject_tunings=build_subject_tunings(calibration))
    tuned_results = tuned_runner.run_suite(cases)
    tuned_report = BenchmarkReportBuilder().build(tuned_results)
    print()
    print('==== TUNED RUN ====')
    print(tuned_report.to_text())


if __name__ == '__main__':
    main()
