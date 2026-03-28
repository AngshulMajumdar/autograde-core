from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autograde.executor import GradingExecutor
from autograde.ingestion import SubmissionIngestionPipeline
from autograde.rubric import Criterion, Rubric, RubricValidator, ScoringPolicy
from autograde.utils.sample_data import build_sample_submission


def test_confidence_and_validation_demo() -> None:
    rubric = Rubric(
        assignment_id="R1",
        assignment_title="Validation Demo",
        required_artifacts=["report"],
        criteria=[
            Criterion(
                criterion_id="C1",
                name="Method",
                description="Check method description.",
                max_score=10,
                weight=0.7,
                required_modalities=["text"],
                evaluation_dimensions=["clarity"],
                evaluator_hints=["text_quality", "argumentation"],
                scoring_policy=ScoringPolicy(mode="weighted_average"),
            ),
            Criterion(
                criterion_id="C2",
                name="Results",
                description="Check result presentation.",
                max_score=10,
                weight=0.2,
                required_modalities=["table"],
                evaluation_dimensions=["clarity"],
                evaluator_hints=["requirements_coverage"],
                scoring_policy=ScoringPolicy(mode="weighted_average"),
            ),
        ],
    )
    validator = RubricValidator()
    validation = validator.validate(rubric)
    assert validation.is_valid
    assert validation.warnings

    submission_dir = ROOT / "tests" / "runtime_confidence_submission"
    build_sample_submission(submission_dir)
    submission = SubmissionIngestionPipeline().ingest_submission("sub_conf", "student_conf", str(submission_dir))
    result = GradingExecutor().grade_submission(submission, rubric)
    assert result.rubric_warnings
    assert any(cr.confidence_rationale for cr in result.criterion_results)
    assert all(isinstance(cr.confidence_factors, list) for cr in result.criterion_results)


def test_invalid_rubric_raises() -> None:
    rubric = Rubric(
        assignment_id="R2",
        assignment_title="Bad",
        required_artifacts=[],
        criteria=[
            Criterion(
                criterion_id="C1",
                name="Bad",
                description="",
                max_score=0,
                weight=-1.0,
                required_modalities=["text"],
                evaluation_dimensions=["clarity"],
                evaluator_hints=["text_quality"],
                scoring_policy=ScoringPolicy(mode="unsupported_mode"),
            )
        ],
    )
    validation = RubricValidator().validate(rubric)
    assert not validation.is_valid
