from __future__ import annotations

from autograde.coverage.aspect_model import CriterionAspect
from autograde.rubric import Criterion, Rubric, ScoringPolicy


def lab_report_template(assignment_id: str, assignment_title: str) -> Rubric:
    criteria = [
        Criterion(
            criterion_id="L1",
            name="Experimental setup and methodology",
            description="Assess whether the submission clearly describes the experimental setup, procedure, and measured variables.",
            max_score=25.0,
            weight=0.25,
            required_modalities=["text"],
            artifact_scope=["report", "notebook", "text"],
            evaluation_dimensions=["clarity", "completeness", "methodological_soundness"],
            evaluator_hints=["text_quality", "technical_correctness"],
            integrity_policy="review_only",
            integrity_scope="text",
            aspects=[
                CriterionAspect("procedure_present", "The procedure or protocol is described.", True, ["text"], ["paragraph", "markdown_cell"], ["method", "procedure"], 1),
                CriterionAspect("variables_present", "Inputs, outputs, or observed variables are identified.", True, ["text"], ["paragraph", "markdown_cell"], ["variable", "measurement"], 1),
                CriterionAspect("conditions_present", "Experimental conditions or setup details are stated.", True, ["text"], ["paragraph", "markdown_cell"], ["setup", "condition"], 1),
            ],
            metadata={"llm_weight": 0.2, 
                "expected_concepts": [
                    {"name": "method", "synonyms": ["procedure", "protocol", "setup"], "required": True},
                    {"name": "measurement", "synonyms": ["observed", "variable", "recorded"], "required": True},
                ]
            },
        ),
        Criterion(
            criterion_id="L2",
            name="Results and observations",
            description="Assess whether observations or measured results are actually presented.",
            max_score=25.0,
            weight=0.25,
            required_modalities=["text", "table"],
            artifact_scope=["report", "spreadsheet", "text"],
            evaluation_dimensions=["evidence_quality", "completeness"],
            evaluator_hints=["simulation_evidence", "result_analysis", "text_quality"],
            scoring_policy=ScoringPolicy(mode="analytic_bands"),
            integrity_policy="review_only",
            integrity_scope="text",
            aspects=[
                CriterionAspect("results_present", "The submission presents observations, data, or result tables.", True, ["table", "text"], ["csv_table", "paragraph"], ["result", "observation"], 1),
                CriterionAspect("metrics_or_units", "Measurements include identifiable quantities, metrics, or units.", True, ["table", "text"], ["csv_table", "paragraph"], ["measurement", "unit", "temperature", "accuracy"], 1),
            ],
        ),
        Criterion(
            criterion_id="L3",
            name="Interpretation and scientific reasoning",
            description="Assess whether the report interprets results rather than merely listing them.",
            max_score=30.0,
            weight=0.30,
            required_modalities=["text", "table"],
            artifact_scope=["report", "text", "spreadsheet"],
            evaluation_dimensions=["justification", "coherence", "technical_depth"],
            evaluator_hints=["result_analysis", "argumentation", "subjective_answer_quality", "cross_modal_consistency"],
            cross_checks=["claims_match_figures"],
            integrity_policy="discount_if_relevant",
            integrity_scope="text",
            aspects=[
                CriterionAspect("interpretation_present", "The report explains what the results mean.", True, ["text"], ["paragraph", "markdown_cell"], ["interpretation", "therefore", "suggests"], 1),
                CriterionAspect("claim_support", "Interpretive claims are tied to actual observations or measurements.", True, ["text", "table"], ["paragraph", "csv_table"], ["result", "observed", "measured"], 1),
                CriterionAspect("limitation_or_error", "The report acknowledges limitations, uncertainty, or sources of error.", False, ["text"], ["paragraph", "markdown_cell"], ["limitation", "error", "uncertainty"], 1),
            ],
            metadata={"llm_weight": 0.2, 
                "length_band": "medium",
                "expected_concepts": [
                    {"name": "interpretation", "synonyms": ["suggests", "indicates", "therefore"], "required": True},
                    {"name": "limitation", "synonyms": ["error", "uncertainty", "source of error"], "required": False},
                ],
            },
        ),
        Criterion(
            criterion_id="L4",
            name="Scientific communication",
            description="Assess clarity, organization, and report quality.",
            max_score=20.0,
            weight=0.20,
            required_modalities=["text"],
            artifact_scope=["report", "text"],
            evaluation_dimensions=["clarity", "organization"],
            evaluator_hints=["text_quality", "requirements_coverage"],
            integrity_policy="review_only",
            integrity_scope="text",
            scoring_policy=ScoringPolicy(mode="weighted_average"),
            aspects=[
                CriterionAspect("report_present", "A report-like explanatory artifact is present.", True, ["text"], ["paragraph", "markdown_cell"], [], 2),
            ],
        ),
    ]
    return Rubric(
        assignment_id=assignment_id,
        assignment_title=assignment_title,
        required_artifacts=["report"],
        criteria=criteria,
    )


def experimental_project_template(assignment_id: str, assignment_title: str) -> Rubric:
    rubric = lab_report_template(assignment_id, assignment_title)
    rubric.criteria[2].criterion_id = "XP3"
    rubric.criteria[2].name = "Interpretation, comparison, and limitations"
    rubric.criteria[2].aspects.append(
        CriterionAspect(
            "comparison_present",
            "The report compares conditions, runs, or baseline behavior where relevant.",
            False,
            ["text", "table"],
            ["paragraph", "csv_table"],
            ["comparison", "baseline", "condition"],
            1,
        )
    )
    return rubric
