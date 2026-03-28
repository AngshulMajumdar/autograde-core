from __future__ import annotations

from pathlib import Path

from autograde.benchmarks import BenchmarkReporter, BenchmarkRunner, SyntheticBenchmarkGenerator


def _reset_dir(root: Path) -> None:
    if root.exists():
        for path in sorted(root.rglob('*'), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()


def main() -> None:
    root = Path('/mnt/data/v21/tests/runtime_benchmarks_suite')
    _reset_dir(root)
    generator = SyntheticBenchmarkGenerator(seed=101)
    cases = generator.generate_suite(str(root), cases_per_subject=4)
    assert len(cases) == 20

    runner = BenchmarkRunner()
    results = runner.run_suite(cases)
    summary = BenchmarkReporter().summarize(results)
    text = BenchmarkReporter().to_text(results)
    print(text)

    assert summary.total_cases == 20
    assert set(summary.by_subject.keys()) == {'programming', 'humanities', 'engineering', 'lab_science', 'mathematics'}
    assert 0 <= summary.passed_cases <= 20
    assert 0.0 <= summary.review_rate <= 1.0
    assert any(r.review_required for r in results)
    assert any('partially_graded' in r.statuses or 'escalated' in r.statuses or 'unsupported_needs_review' in r.statuses for r in results)


if __name__ == '__main__':
    main()
