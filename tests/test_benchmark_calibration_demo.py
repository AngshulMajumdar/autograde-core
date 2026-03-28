from __future__ import annotations

from pathlib import Path

from autograde.benchmarks import BenchmarkReporter, BenchmarkRunner, BenchmarkTuner, SyntheticBenchmarkGenerator


def _reset_dir(root: Path) -> None:
    if root.exists():
        for path in sorted(root.rglob('*'), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()


def main() -> None:
    root = Path('/mnt/data/v22/tests/runtime_benchmark_calibration_suite')
    _reset_dir(root)
    cases = SyntheticBenchmarkGenerator(seed=123).generate_suite(str(root), cases_per_subject=4)
    results = BenchmarkRunner().run_suite(cases)
    summary = BenchmarkReporter().summarize(results)
    calibration = BenchmarkTuner().calibrate(results)
    text = calibration.to_text()
    print(text)

    assert summary.total_cases == 20
    assert calibration.subjects
    assert set(calibration.subjects.keys()) == {'programming', 'humanities', 'engineering', 'lab_science', 'mathematics'}
    for subject, subject_report in calibration.subjects.items():
        assert 0.4 <= subject_report.suggested_low_confidence_threshold <= 0.8
        assert subject_report.suggested_review_bias in {'balanced', 'more_review', 'less_review'}


if __name__ == '__main__':
    main()
