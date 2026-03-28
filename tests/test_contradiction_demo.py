from __future__ import annotations

from pathlib import Path

from autograde.executor import GradingExecutor
from autograde.ingestion import SubmissionIngestionPipeline
from autograde.outputs import ReportFormatter
from autograde.rubric import Criterion, Rubric, ScoringPolicy
from autograde.utils.sample_data import build_contradictory_submission


def build_rubric() -> Rubric:
    return Rubric(
        assignment_id="CS301_A3",
        assignment_title="Contradiction Test",
        required_artifacts=["report", "source_code"],
        criteria=[
            Criterion(
                criterion_id="C1",
                name="Implementation and report consistency",
                description="Assess consistency between report claims, code, and reported metrics.",
                max_score=20,
                weight=1.0,
                required_modalities=["text", "code", "table"],
                evaluation_dimensions=["correctness", "consistency"],
                artifact_scope=["report", "source_code", "notebook", "spreadsheet"],
                cross_checks=["report_matches_code", "claims_match_figures"],
                cross_check_policy="binding",
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
    root = Path("/mnt/data/ag_v5/tests/runtime_contradictory_submission")
    _reset_dir(root)
    build_contradictory_submission(str(root))

    pipeline = SubmissionIngestionPipeline()
    submission = pipeline.ingest_submission(
        assignment_id="CS301_A3",
        submission_path=str(root),
        submission_id="sub_contra_001",
        student_id="2021CS9999",
    )

    rubric = build_rubric()
    executor = GradingExecutor()
    result = executor.grade_submission(submission, rubric)

    print(ReportFormatter.student_feedback(result))

    flags = result.criterion_results[0].flags
    contradiction_flags = [f for f in flags if f.get("type") == "contradiction"]
    assert contradiction_flags, "Expected contradiction flags to be raised"
    assert result.criterion_results[0].status in {"escalated", "graded"}
    assert result.criterion_results[0].manual_review_required is True
    assert any(cr.get("type") in {"algorithm_mismatch", "metric_value_mismatch", "metric_threshold_mismatch"} for cr in result.criterion_results[0].contradiction_results)


if __name__ == "__main__":
    main()
