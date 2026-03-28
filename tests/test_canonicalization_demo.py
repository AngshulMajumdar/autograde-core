from __future__ import annotations

import json
from pathlib import Path

from autograde.executor import ClaimGraphBuilder, GradingExecutor
from autograde.ingestion import SubmissionIngestionPipeline
from autograde.rubric import Criterion, Rubric, ScoringPolicy


def build_canonical_submission(root: str) -> None:
    base = Path(root)
    base.mkdir(parents=True, exist_ok=True)
    (base / "report.txt").write_text(
        """Title: Canonicalization Report

We implemented Dijkstra's algorithm for shortest paths. The report also notes that the method uses a priority queue and achieves accuracy above 98%.

The asymptotic complexity is O(n log n).
""",
        encoding="utf-8",
    )
    (base / "main.py").write_text(
        """import heapq

def dijkstra(graph, src):
    pq = [(0, src)]
    while pq:
        d, u = heapq.heappop(pq)
        return {}
""",
        encoding="utf-8",
    )
    notebook = {
        "cells": [{"cell_type": "markdown", "source": ["# Notes\n", "Uses heap based implementation.\n"]}],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    (base / "analysis.ipynb").write_text(json.dumps(notebook), encoding="utf-8")
    (base / "results.csv").write_text("dataset,acc\nbench,98\n", encoding="utf-8")


def build_rubric() -> Rubric:
    return Rubric(
        assignment_id="CS301_A5",
        assignment_title="Canonicalization Test",
        required_artifacts=["report", "source_code"],
        criteria=[
            Criterion(
                criterion_id="C1",
                name="Consistency",
                description="Assess consistency after canonicalization.",
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
    root = Path("/mnt/data/ag_v6/tests/runtime_canonical_submission")
    _reset_dir(root)
    build_canonical_submission(str(root))

    pipeline = SubmissionIngestionPipeline()
    submission = pipeline.ingest_submission(
        assignment_id="CS301_A5",
        submission_path=str(root),
        submission_id="sub_canon_001",
        student_id="2021CS7777",
    )

    graph = ClaimGraphBuilder().build(submission.submission_id, submission.evidence)
    algorithm_values = {node.value for node in graph.nodes if node.subject == "algorithm"}
    metric_values = {node.value for node in graph.nodes if node.subject == "accuracy"}
    assert "dijkstra" in algorithm_values, algorithm_values
    assert 0.98 in metric_values, metric_values

    result = GradingExecutor().grade_submission(submission, build_rubric())
    contradictions = result.criterion_results[0].contradiction_results
    contradiction_types = {c["type"] for c in contradictions}
    assert "algorithm_mismatch" not in contradiction_types, contradictions
    assert "metric_threshold_mismatch" not in contradiction_types, contradictions
    assert result.criterion_results[0].manual_review_required is False, result.criterion_results[0].flags
    print(result.claim_graph_summary)


if __name__ == "__main__":
    main()
