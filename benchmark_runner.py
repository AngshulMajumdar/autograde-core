from __future__ import annotations

from pathlib import Path

from autograde.benchmarks import BenchmarkReporter, BenchmarkRunner, SyntheticBenchmarkGenerator


def main() -> None:
    base = Path('/mnt/data/autograde_synthetic_benchmarks')
    cases = SyntheticBenchmarkGenerator(seed=13).generate_suite(str(base), cases_per_subject=8)
    results = BenchmarkRunner().run_suite(cases)
    print(BenchmarkReporter().to_text(results))


if __name__ == '__main__':
    main()
