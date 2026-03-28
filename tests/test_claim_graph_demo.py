from __future__ import annotations

from pathlib import Path

from autograde.executor import ClaimGraphBuilder, GradingExecutor
from autograde.ingestion import SubmissionIngestionPipeline
from autograde.rubric import Criterion, Rubric, ScoringPolicy
from autograde.utils.sample_data import build_contradictory_submission


def build_rubric() -> Rubric:
    return Rubric(
        assignment_id="CS301_A4",
        assignment_title="Claim Graph Test",
        required_artifacts=["report", "source_code"],
        criteria=[
            Criterion(
                criterion_id="C1",
                name="Consistency",
                description="Check consistency between claims and artifacts.",
                max_score=20,
                weight=1.0,
                required_modalities=["text", "code", "table"],
                evaluation_dimensions=["consistency"],
                artifact_scope=["report", "source_code", "spreadsheet"],
                cross_check_policy="binding",
                scoring_policy=ScoringPolicy(mode="weighted_average"),
            )
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
    root = Path("/mnt/data/ag_v5/tests/runtime_claim_graph_submission")
    _reset_dir(root)
    build_contradictory_submission(str(root))

    pipeline = SubmissionIngestionPipeline()
    submission = pipeline.ingest_submission(
        assignment_id="CS301_A4",
        submission_path=str(root),
        submission_id="sub_claim_001",
        student_id="2021CS0001",
    )

    graph = ClaimGraphBuilder().build(submission.submission_id, submission.evidence)
    summary = graph.summary()
    assert summary["claim_count"] > 0
    assert summary["edge_count"] > 0
    assert "algorithm_claim" in summary["claim_types"] or "metric_claim" in summary["claim_types"]

    result = GradingExecutor().grade_submission(submission, build_rubric())
    assert result.claim_graph_summary["claim_count"] == summary["claim_count"]
    assert result.claim_graph_summary["edge_count"] == summary["edge_count"]
    print(result.claim_graph_summary)


if __name__ == "__main__":
    main()
