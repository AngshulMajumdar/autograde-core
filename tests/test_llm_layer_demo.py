from __future__ import annotations

from autograde.executor import GradingExecutor
from autograde.models import Artifact, EvidenceObject, Submission
from autograde.rubric import Criterion, Rubric, ScoringPolicy


def build_submission() -> Submission:
    submission = Submission(
        submission_id="sub_llm",
        assignment_id="A1",
        student_id="s1",
        submitted_at=None,
    )
    submission.add_artifact(
        Artifact(
            artifact_id="a1",
            submission_id="sub_llm",
            file_name="essay.txt",
            artifact_type="text",
            mime_type="text/plain",
            storage_path="essay.txt",
            checksum="x",
            size_bytes=10,
            parse_status="parsed",
        )
    )
    submission.add_evidence(
        EvidenceObject(
            evidence_id="ev1",
            submission_id="sub_llm",
            artifact_id="a1",
            modality="text",
            subtype="essay",
            content=(
                "The thesis is that public policy should support open access because it improves scientific dissemination. "
                "However, funding models must be adjusted. For example, publication subsidies can reduce inequity. "
                "Therefore the argument balances access and sustainability."
            ),
            structured_content={},
            preview="open access policy argument",
            location={"page": 1},
            confidence=0.98,
            extractor_id="manual",
            tags=["thesis", "argument"],
            links=[],
        )
    )
    return submission


def build_rubric() -> Rubric:
    criterion = Criterion(
        criterion_id="H1",
        name="Argument quality",
        description="Evaluate thesis clarity and argument development.",
        max_score=20,
        weight=1.0,
        required_modalities=["text"],
        evaluation_dimensions=["coherence", "justification"],
        evaluator_hints=["thesis_strength", "llm_argument_quality"],
        scoring_policy=ScoringPolicy(mode="weighted_average"),
        metadata={"llm_weight": 0.3},
    )
    return Rubric(
        assignment_id="A1",
        assignment_title="Essay",
        required_artifacts=["text"],
        criteria=[criterion],
        normalize_to=100.0,
    )


def test_llm_layer_demo(monkeypatch):
    monkeypatch.setenv("AUTOGRADE_LLM_PROVIDER", "mock")
    result = GradingExecutor().grade_submission(build_submission(), build_rubric())
    assert result.final_score > 0
    crit = result.criterion_results[0]
    llm_results = [r for r in crit.evaluator_results if r.evaluator_id.startswith("llm_")]
    assert llm_results
    assert llm_results[0].flags and llm_results[0].flags[0]["type"] == "llm_evaluation"
