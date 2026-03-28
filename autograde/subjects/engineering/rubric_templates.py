from __future__ import annotations

from autograde.coverage.aspect_model import CriterionAspect
from autograde.rubric import Criterion, Rubric, ScoringPolicy


def circuit_design_template(assignment_id: str, assignment_title: str) -> Rubric:
    criteria = [
        Criterion(
            criterion_id="G1",
            name="Diagram completeness and labeling",
            description="Check whether the submitted circuit contains the expected structural elements and labels.",
            max_score=20.0,
            weight=0.20,
            required_modalities=["diagram"],
            artifact_scope=["design_diagram"],
            evaluation_dimensions=["completeness", "clarity"],
            evaluator_hints=["diagram_completeness", "requirements_coverage"],
            integrity_policy="review_only",
            integrity_scope="all",
            aspects=[
                CriterionAspect("components_present", "Core circuit components are present.", True, ["diagram"], ["design_diagram"], ["op_amp", "resistor"], 1),
                CriterionAspect("labels_present", "Important nodes or components are labeled.", True, ["diagram"], ["design_diagram"], [], 1),
            ],
            metadata={"llm_weight": 0.2, "required_components": ["op_amp", "input_node", "output_node"]},
        ),
        Criterion(
            criterion_id="G2",
            name="Functional plausibility",
            description="Assess whether the circuit satisfies the required design family or appears plausibly correct under the stated constraints.",
            max_score=30.0,
            weight=0.30,
            required_modalities=["diagram", "text"],
            artifact_scope=["design_diagram", "text", "spreadsheet"],
            evaluation_dimensions=["correctness", "justification"],
            evaluator_hints=["topology_constraint_satisfaction", "design_functional_plausibility", "alternative_design_plausibility", "cross_modal_consistency"],
            cross_checks=["diagram_matches_text"],
            cross_check_policy="advisory",
            integrity_policy="review_only",
            integrity_scope="all",
            aspects=[
                CriterionAspect("signal_path", "The design exposes a meaningful input-output path.", True, ["diagram"], ["design_diagram"], ["input_node", "output_node"], 1),
                CriterionAspect("feedback_or_control", "Feedback or the relevant control relation is represented when required.", True, ["diagram"], ["design_diagram"], ["feedback_path"], 1),
                CriterionAspect("design_explanation", "The report explains why the design works.", True, ["text"], ["paragraph"], ["design_explanation"], 1),
            ],
            metadata={"llm_weight": 0.2, 
                "accepted_families": ["op_amp_feedback_family", "active_filter_family"],
                "required_components": ["op_amp", "input_node", "output_node", "feedback_path"],
                "expected_topology": {"requires_feedback": True, "min_nodes": 3, "min_edges": 1},
            },
            manual_review_conditions=["low_confidence"],
        ),
        Criterion(
            criterion_id="G3",
            name="Behavioral evidence and simulation support",
            description="Check whether the submitted measurements or simulation outputs support the claimed circuit behavior.",
            max_score=25.0,
            weight=0.25,
            required_modalities=["table", "text"],
            artifact_scope=["spreadsheet", "text"],
            evaluation_dimensions=["evidence_quality", "consistency"],
            evaluator_hints=["simulation_evidence", "behavioral_metric_alignment", "simulation_consistency", "cross_modal_consistency"],
            cross_checks=["claims_match_figures"],
            cross_check_policy="advisory",
            integrity_policy="review_only",
            integrity_scope="text",
            aspects=[
                CriterionAspect("simulation_values", "Simulation or measured values are provided.", True, ["table"], ["csv_table"], [], 1),
                CriterionAspect("behavior_claims", "The report states the behavioral outcome of the design.", True, ["text"], ["paragraph"], ["behavior_claim"], 1),
            ],
            metadata={"expected_metrics": ["gain", "cutoff"], "target_behavior": "low_pass"},
        ),
        Criterion(
            criterion_id="G4",
            name="Design justification and communication",
            description="Assess how clearly the design decisions are justified in the report.",
            max_score=25.0,
            weight=0.25,
            required_modalities=["text", "diagram"],
            artifact_scope=["text", "design_diagram"],
            evaluation_dimensions=["clarity", "justification"],
            evaluator_hints=["design_report_alignment", "text_quality", "cross_modal_consistency", "argumentation"],
            integrity_policy="discount_if_relevant",
            integrity_scope="text",
            integrity_severity_threshold="high",
            aspects=[
                CriterionAspect("design_rationale", "The report justifies the chosen topology.", True, ["text"], ["paragraph"], ["design_explanation"], 1),
                CriterionAspect("constraint_reference", "The report references the required design constraints or target behavior.", True, ["text"], ["paragraph"], ["target_behavior"], 1),
            ],
            scoring_policy=ScoringPolicy(mode="weighted_average"),
        ),
    ]
    return Rubric(
        assignment_id=assignment_id,
        assignment_title=assignment_title,
        required_artifacts=["design_diagram", "text"],
        criteria=criteria,
    )
