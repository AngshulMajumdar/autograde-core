from __future__ import annotations

from autograde.models import CriterionResult
from autograde.executor.adaptive_weighting import AdaptiveWeightingEngine
from autograde.rubric import Criterion, Rubric, ScoringPolicy


def build_rubric():
    return Rubric(
        assignment_id="adaptive-demo",
        assignment_title="Adaptive weighting demo",
        required_artifacts=["report"],
        adaptive_weighting_enabled=True,
        adaptive_weighting_params={"min_factor": 0.6, "max_factor": 1.4},
        criteria=[
            Criterion(
                criterion_id="C1",
                name="Strong evidence criterion",
                description="Strong evidence",
                max_score=20,
                weight=0.5,
                required_modalities=["text"],
                evaluation_dimensions=["clarity"],
                scoring_policy=ScoringPolicy(mode="analytic_bands"),
            ),
            Criterion(
                criterion_id="C2",
                name="Weak evidence criterion",
                description="Weak evidence",
                max_score=20,
                weight=0.5,
                required_modalities=["text"],
                evaluation_dimensions=["clarity"],
                scoring_policy=ScoringPolicy(mode="analytic_bands"),
            ),
        ],
    )


def test_adaptive_weighting_prefers_stronger_evidence():
    rubric = build_rubric()
    engine = AdaptiveWeightingEngine()
    strong = CriterionResult(
        criterion_id="C1",
        score=12,
        max_score=20,
        confidence=0.92,
        rationale="",
        coverage_status="covered",
        capability_status="supported",
        support_status="supported",
        contradiction_results=[],
        claim_evidence_results=[{"status": "supported"}],
        status="graded",
    )
    weak = CriterionResult(
        criterion_id="C2",
        score=18,
        max_score=20,
        confidence=0.38,
        rationale="",
        coverage_status="missing_required",
        capability_status="supported",
        support_status="partial",
        contradiction_results=[{"severity": "high"}],
        claim_evidence_results=[{"status": "contradicted"}],
        status="partially_graded",
    )
    decisions = {d.criterion_id: d for d in engine.apply([strong, weak], rubric)}
    assert decisions["C1"].adjusted_weight > decisions["C2"].adjusted_weight
    assert decisions["C1"].evidence_strength > decisions["C2"].evidence_strength
