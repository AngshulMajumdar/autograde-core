from __future__ import annotations

from pathlib import Path

from autograde.executor import GradingExecutor
from autograde.ingestion import SubmissionIngestionPipeline
from autograde.integrity import ExternalSource
from autograde.outputs import ReportFormatter
from autograde.rubric import Criterion, Rubric, ScoringPolicy
from autograde.utils.sample_data import build_sample_submission


def build_rubric() -> Rubric:
    return Rubric(
        assignment_id="CS301_A2",
        assignment_title="Data Structures Project",
        required_artifacts=["report", "source_code"],
        criteria=[
            Criterion(
                criterion_id="C1",
                name="Report quality",
                description="Assess clarity and argument quality in the report.",
                max_score=20,
                weight=0.4,
                required_modalities=["text"],
                evaluation_dimensions=["clarity", "coherence"],
                artifact_scope=["report", "text"],
                scoring_policy=ScoringPolicy(mode="analytic_bands"),
            ),
            Criterion(
                criterion_id="C2",
                name="Implementation quality",
                description="Assess code quality and correctness signals.",
                max_score=20,
                weight=0.4,
                required_modalities=["code"],
                evaluation_dimensions=["correctness"],
                evaluator_hints=["code_quality"],
                artifact_scope=["source_code", "notebook"],
                scoring_policy=ScoringPolicy(mode="gated_score", params={"gate_on": "technical_correctness", "gate_threshold": 0.5, "cap_fraction": 0.4}),
            ),
            Criterion(
                criterion_id="C3",
                name="Report-code consistency",
                description="Assess whether report and code align conceptually.",
                max_score=10,
                weight=0.2,
                required_modalities=["text", "code"],
                evaluation_dimensions=["consistency"],
                artifact_scope=["report", "source_code", "notebook"],
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
    root = Path("/mnt/data/autograde_core/tests/runtime_submission")
    cohort_root = Path("/mnt/data/autograde_core/tests/runtime_submission_2")
    _reset_dir(root)
    _reset_dir(cohort_root)
    build_sample_submission(str(root))
    build_sample_submission(str(cohort_root))
    (cohort_root / "report.txt").write_text(
        (cohort_root / "report.txt").read_text(encoding="utf-8").replace("toy graph", "small graph"),
        encoding="utf-8",
    )

    pipeline = SubmissionIngestionPipeline()
    submission = pipeline.ingest_submission(
        assignment_id="CS301_A2",
        submission_path=str(root),
        submission_id="sub_001",
        student_id="2021CS0001",
    )
    submission2 = pipeline.ingest_submission(
        assignment_id="CS301_A2",
        submission_path=str(cohort_root),
        submission_id="sub_002",
        student_id="2021CS0002",
    )

    rubric = build_rubric()
    executor = GradingExecutor()
    result = executor.grade_submission(
        submission,
        rubric,
        source_corpus=[ExternalSource(source_id="sample_source", text="An unrelated external source about sorting algorithms.")],
    )
    cohort_flags = executor.grade_cohort_similarity([submission, submission2])

    print("Artifacts:", len(submission.artifacts))
    print("Evidence:", len(submission.evidence))
    print("Cohort flags:", cohort_flags)
    print(ReportFormatter.student_feedback(result))

    assert len(submission.artifacts) == 4
    assert len(submission.evidence) >= 6
    assert result.final_score > 0
    assert len(result.criterion_results) == 3
    assert any(cr.status in {"graded", "escalated", "insufficient_evidence"} for cr in result.criterion_results)
    assert any(flag["type"] == "intra_cohort_similarity" for flag in cohort_flags)


if __name__ == "__main__":
    main()
