from __future__ import annotations

from autograde.coverage.aspect_model import CriterionAspect
from autograde.rubric import Criterion, Rubric, ScoringPolicy


def proof_template(assignment_id: str, assignment_title: str) -> Rubric:
    criteria = [
        Criterion(
            criterion_id="M1",
            name="Problem understanding and setup",
            description="Assess whether the submission states the goal, assumptions, or relevant setup clearly.",
            max_score=20.0,
            weight=0.20,
            required_modalities=["text"],
            artifact_scope=["report", "text", "image"],
            evaluation_dimensions=["clarity", "relevance"],
            evaluator_hints=["proof_validity", "theorem_definition_use", "text_quality", "subjective_answer_quality"],
            integrity_policy="review_only",
            integrity_scope="text",
            aspects=[
                CriterionAspect("goal_present", "The statement to be shown or derived is identified.", True, ["text"], ["paragraph"], ["show", "prove", "derive", "goal"], 1),
                CriterionAspect("assumptions_present", "Relevant assumptions or givens are stated.", True, ["text"], ["paragraph"], ["assume", "given", "let"], 1),
            ],
            metadata={"llm_weight": 0.2, "accept_ocr": True, "prefer_equation_evidence": True, 
                "length_band": "short",
                "expected_concepts": [
                    {"name": "goal", "synonyms": ["prove", "show", "derive"], "required": True},
                    {"name": "assume", "synonyms": ["given", "let"], "required": True},
                ],
            },
        ),
        Criterion(
            criterion_id="M2",
            name="Logical development",
            description="Assess whether the solution develops through explicit intermediate reasoning steps rather than unsupported jumps.",
            max_score=35.0,
            weight=0.35,
            required_modalities=["text"],
            artifact_scope=["report", "text", "image"],
            evaluation_dimensions=["coherence", "justification", "technical_depth"],
            evaluator_hints=["proof_validity", "derivation_step_quality", "theorem_definition_use", "argumentation", "subjective_answer_quality"],
            scoring_policy=ScoringPolicy(mode="weighted_average"),
            integrity_policy="review_only",
            integrity_scope="text",
            aspects=[
                CriterionAspect("step_sequence", "The proof or derivation proceeds through identifiable steps.", True, ["text"], ["paragraph"], ["therefore", "thus", "hence", "since"], 1),
                CriterionAspect("justification_present", "Important transitions are justified.", True, ["text"], ["paragraph"], ["because", "by", "using", "therefore"], 1),
            ],
            metadata={"llm_weight": 0.2, "accept_ocr": True, "prefer_equation_evidence": True, 
                "length_band": "medium",
                "expected_concepts": [
                    {"name": "therefore", "synonyms": ["thus", "hence"], "required": True},
                    {"name": "because", "synonyms": ["by", "using", "since"], "required": True},
                ],
            },
        ),
        Criterion(
            criterion_id="M3",
            name="Completeness and conclusion",
            description="Assess whether the submission actually closes the proof or derivation and reaches the intended statement.",
            max_score=25.0,
            weight=0.25,
            required_modalities=["text"],
            artifact_scope=["report", "text", "image"],
            evaluation_dimensions=["completeness", "consistency"],
            evaluator_hints=["subjective_answer_quality", "conclusion_target_alignment", "cross_modal_consistency"],
            scoring_policy=ScoringPolicy(mode="analytic_bands"),
            integrity_policy="review_only",
            integrity_scope="text",
            aspects=[
                CriterionAspect("conclusion_present", "A closing statement indicates what has been shown or derived.", True, ["text"], ["paragraph"], ["therefore", "hence", "we conclude", "proved"], 1),
                CriterionAspect("target_reached", "The conclusion aligns with the stated goal.", True, ["text"], ["paragraph"], ["show", "prove", "derive", "conclude"], 1),
            ],
            metadata={"llm_weight": 0.2, "accept_ocr": True, "prefer_equation_evidence": True, 
                "length_band": "medium",
                "expected_concepts": [
                    {"name": "conclude", "synonyms": ["therefore", "hence", "proved"], "required": True},
                ],
            },
        ),
        Criterion(
            criterion_id="M4",
            name="Mathematical communication",
            description="Assess clarity and organization of the presented reasoning.",
            max_score=20.0,
            weight=0.20,
            required_modalities=["text"],
            artifact_scope=["report", "text", "image"],
            evaluation_dimensions=["clarity", "organization"],
            evaluator_hints=["text_quality"],
            integrity_policy="review_only",
            integrity_scope="text",
            scoring_policy=ScoringPolicy(mode="weighted_average"),
            aspects=[
                CriterionAspect("readable_solution", "The solution is readable and organized enough to follow.", True, ["text"], ["paragraph"], [], 2),
            ],
        ),
    ]
    return Rubric(
        assignment_id=assignment_id,
        assignment_title=assignment_title,
        required_artifacts=[],
        criteria=criteria,
    )


def derivation_template(assignment_id: str, assignment_title: str) -> Rubric:
    rubric = proof_template(assignment_id, assignment_title)
    rubric.criteria[0].criterion_id = "D1"
    rubric.criteria[0].name = "Setup and starting expression"
    rubric.criteria[1].criterion_id = "D2"
    rubric.criteria[1].name = "Stepwise derivation quality"
    rubric.criteria[2].criterion_id = "D3"
    rubric.criteria[2].name = "Final expression and completeness"
    rubric.criteria[3].criterion_id = "D4"
    rubric.criteria[3].name = "Presentation and notation clarity"
    return rubric
