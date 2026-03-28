from __future__ import annotations

from autograde.coverage.aspect_model import CriterionAspect
from autograde.rubric import Criterion, Rubric, ScoringPolicy


def programming_project_template(assignment_id: str, assignment_title: str) -> Rubric:
    return Rubric(
        assignment_id=assignment_id,
        assignment_title=assignment_title,
        required_artifacts=["report", "source_code"],
        criteria=[
            Criterion(
                criterion_id="P1",
                name="Implementation behavior",
                description="Assess whether the recovered implementation behaves correctly under controlled unit probes.",
                max_score=25,
                weight=0.30,
                required_modalities=["code", "execution"],
                evaluation_dimensions=["behavior"],
                evaluator_hints=["behavioral_correctness"],
                artifact_scope=["source_code"],
                scoring_policy=ScoringPolicy(mode="gated_score", params={"gate_evaluator": "behavioral_correctness", "gate_threshold": 0.5, "cap_fraction": 0.4}),
                integrity_policy="block_if_high",
                integrity_scope="code",
                aspects=[
                    CriterionAspect(
                        aspect_id="callable_core_present",
                        description="At least one meaningful callable implementation unit is recoverable.",
                        required=True,
                        modalities=["code"],
                        evidence_types=["function", "class"],
                    ),
                    CriterionAspect(
                        aspect_id="behavioral_evidence_present",
                        description="Execution probe evidence exists for the recovered implementation.",
                        required=True,
                        modalities=["execution"],
                        evidence_types=["unit_test_result"],
                    ),
                ],
            ),
            Criterion(
                criterion_id="P2",
                name="Code quality and software structure",
                description="Assess readability, decomposition, and visible software organization.",
                max_score=20,
                weight=0.20,
                required_modalities=["code"],
                evaluation_dimensions=["correctness"],
                evaluator_hints=["code_quality"],
                artifact_scope=["source_code", "notebook"],
                scoring_policy=ScoringPolicy(mode="weighted_average"),
                integrity_policy="review_only",
                integrity_scope="code",
                aspects=[
                    CriterionAspect(
                        aspect_id="core_code_present",
                        description="Submission contains substantive implementation code.",
                        required=True,
                        modalities=["code"],
                        evidence_types=["function", "class"],
                        min_evidence_count=1,
                    ),
                ],
            ),
            Criterion(
                criterion_id="P3",
                name="Report–implementation alignment",
                description="Assess whether the report accurately describes the visible implementation and observed behavior.",
                max_score=20,
                weight=0.20,
                required_modalities=["text", "code", "execution"],
                evaluation_dimensions=["implementation_alignment", "consistency"],
                evaluator_hints=["implementation_report_alignment", "cross_modal_consistency"],
                artifact_scope=["report", "source_code", "notebook"],
                cross_checks=["report_matches_code"],
                cross_check_policy="binding",
                scoring_policy=ScoringPolicy(mode="weighted_average"),
                integrity_policy="discount_if_relevant",
                integrity_scope="all",
                aspects=[
                    CriterionAspect(
                        aspect_id="method_claim_present",
                        description="The report states what was implemented.",
                        required=True,
                        modalities=["text"],
                        evidence_types=["paragraph", "markdown_cell"],
                    ),
                    CriterionAspect(
                        aspect_id="implementation_reference_present",
                        description="The code contains a visible implementation corresponding to the reported method.",
                        required=True,
                        modalities=["code"],
                        evidence_types=["function", "class"],
                    ),
                ],
            ),
            Criterion(
                criterion_id="P4",
                name="Experimental evidence and result credibility",
                description="Assess whether reported results are present, stated clearly, and supported by submitted evidence.",
                max_score=20,
                weight=0.20,
                required_modalities=["text", "table"],
                evaluation_dimensions=["clarity", "completeness", "consistency"],
                evaluator_hints=["text_quality"],
                artifact_scope=["report", "spreadsheet", "notebook"],
                cross_checks=["claims_match_figures"],
                scoring_policy=ScoringPolicy(mode="analytic_bands"),
                integrity_policy="discount_if_relevant",
                integrity_scope="text",
                aspects=[
                    CriterionAspect(
                        aspect_id="results_present",
                        description="Submission contains explicit result evidence such as tables or logged metrics.",
                        required=True,
                        modalities=["table", "text"],
                        evidence_types=["csv_table", "paragraph"],
                    ),
                    CriterionAspect(
                        aspect_id="metric_claim_present",
                        description="The report or notebook states an outcome metric or result claim.",
                        required=True,
                        modalities=["text", "table"],
                        evidence_types=["paragraph", "csv_table"],
                    ),
                    CriterionAspect(
                        aspect_id="interpretation_present",
                        description="The report interprets what the results mean.",
                        required=True,
                        modalities=["text"],
                        evidence_types=["paragraph", "markdown_cell"],
                    ),
                ],
            ),
            Criterion(
                criterion_id="P5",
                name="Technical communication",
                description="Assess clarity, organization, and argumentative quality of the report.",
                max_score=15,
                weight=0.10,
                required_modalities=["text"],
                evaluation_dimensions=["clarity", "coherence", "organization", "justification"],
                evaluator_hints=["text_quality", "argumentation"],
                artifact_scope=["report", "notebook"],
                scoring_policy=ScoringPolicy(mode="weighted_average"),
                integrity_policy="review_only",
                integrity_scope="text",
                aspects=[
                    CriterionAspect(
                        aspect_id="report_present",
                        description="A report-like explanatory artifact is present.",
                        required=True,
                        modalities=["text"],
                        evidence_types=["paragraph", "markdown_cell"],
                        min_evidence_count=2,
                    ),
                ],
            ),
        ],
        normalize_to=100.0,
    )


def programming_lab_template(assignment_id: str, assignment_title: str) -> Rubric:
    rubric = programming_project_template(assignment_id, assignment_title)
    rubric.assignment_title = assignment_title
    rubric.assignment_id = assignment_id
    rubric.criteria[3].criterion_id = "L4"
    rubric.criteria[3].name = "Reproducible experimental results"
    rubric.criteria[3].description = "Assess whether the submission contains reproducible evidence for reported results."
    return rubric


def data_science_notebook_template(assignment_id: str, assignment_title: str) -> Rubric:
    rubric = programming_project_template(assignment_id, assignment_title)
    rubric.required_artifacts = ["notebook", "report"]
    rubric.criteria[0].name = "Notebook implementation behavior"
    rubric.criteria[0].artifact_scope = ["notebook", "source_code"]
    rubric.criteria[1].name = "Code and notebook organization"
    rubric.criteria[1].artifact_scope = ["notebook", "source_code"]
    rubric.criteria[3].name = "Experimental design and result credibility"
    rubric.criteria[3].aspects.append(
        CriterionAspect(
            aspect_id="notebook_flow_present",
            description="Notebook shows a coherent narrative flow between markdown and code.",
            required=False,
            modalities=["metadata"],
            evidence_types=["notebook_flow"],
        )
    )
    rubric.criteria[4].name = "Technical narrative and interpretation"
    return rubric
