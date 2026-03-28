from __future__ import annotations

from autograde.benchmarks.generator import SyntheticBenchmarkGenerator
from autograde.benchmarks.runner import BenchmarkRunner
from autograde.benchmarks.tuner import BenchmarkTuner, build_subject_tunings


def test_tuned_benchmark_demo(tmp_path):
    cases = SyntheticBenchmarkGenerator(seed=9).generate_suite(str(tmp_path / "bench"), cases_per_subject=3)
    baseline = BenchmarkRunner().run_suite(cases)
    report = BenchmarkTuner().calibrate(baseline)
    tunings = build_subject_tunings(report)
    assert 'programming' in tunings
    tuned = BenchmarkRunner(subject_tunings=tunings).run_suite(cases)
    assert len(tuned) == len(baseline)
    assert all(r.subject_id for r in tuned)
