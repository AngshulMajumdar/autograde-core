from __future__ import annotations

from pathlib import Path

from autograde.executor import GradingExecutor
from autograde.ingestion import SubmissionIngestionPipeline
from autograde.outputs import ReportFormatter
from autograde.rubric import Criterion, Rubric, ScoringPolicy
from autograde.utils.sample_data import build_hardcoded_but_probeable_submission


def build_rubric() -> Rubric:
    return Rubric(
        assignment_id="CS301_A6",
        assignment_title="Execution Probe Test",
        required_artifacts=["report", "source_code"],
        criteria=[
            Criterion(
                criterion_id="C1",
                name="Behavioral correctness",
                description="Assess code through recovered callable units and sandboxed unit probes.",
                max_score=20,
                weight=0.6,
                required_modalities=["code"],
                evaluation_dimensions=["behavior"],
                evaluator_hints=["behavioral_correctness"],
                artifact_scope=["source_code"],
                scoring_policy=ScoringPolicy(mode="weighted_average"),
            ),
            Criterion(
                criterion_id="C2",
                name="Implementation-report alignment",
                description="Assess whether the report matches implementation behavior and visible code structure.",
                max_score=20,
                weight=0.4,
                required_modalities=["text", "code"],
                evaluation_dimensions=["implementation_alignment"],
                evaluator_hints=["implementation_report_alignment"],
                artifact_scope=["report", "source_code"],
                scoring_policy=ScoringPolicy(mode="weighted_average"),
            ),
        ],
        normalize_to=100.0,
    )


def _reset_dir(root: Path) -> None:
    if root.exists():
        for path in sorted(root.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()


def main() -> None:
    root = Path("/mnt/data/ag_v8/tests/runtime_probeable_submission")
    _reset_dir(root)
    build_hardcoded_but_probeable_submission(str(root))

    pipeline = SubmissionIngestionPipeline()
    submission = pipeline.ingest_submission(
        assignment_id="CS301_A6",
        submission_path=str(root),
        submission_id="sub_probe_001",
        student_id="2021CS8888",
    )

    result = GradingExecutor().grade_submission(submission, build_rubric())

    print("Execution summary:", submission.submission_metadata.get("execution_probe_summary"))
    print(ReportFormatter.student_feedback(result))

    execution_evidence = [e for e in submission.evidence if e.modality == "execution"]
    assert execution_evidence, "Expected execution evidence to be attached"
    summary = submission.submission_metadata.get("execution_probe_summary", {})
    assert summary.get("callable_units", 0) >= 1, summary
    assert summary.get("tests_run", 0) >= 1, summary
    assert summary.get("tests_passed", 0) >= 1, summary

    behavioral = next(cr for cr in result.criterion_results if cr.criterion_id == "C1")
    assert behavioral.score > 0, behavioral
    assert any(er.evaluator_id == "behavioral_correctness" for er in behavioral.evaluator_results)

    alignment = next(cr for cr in result.criterion_results if cr.criterion_id == "C2")
    assert alignment.score > 0, alignment
    assert any(er.evaluator_id == "implementation_report_alignment" for er in alignment.evaluator_results)


if __name__ == "__main__":
    main()
