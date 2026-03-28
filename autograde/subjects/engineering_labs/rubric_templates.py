from __future__ import annotations

from autograde.coverage.aspect_model import CriterionAspect
from autograde.rubric import Criterion, Rubric, ScoringPolicy


def ee_lab_report_template(assignment_id: str, assignment_title: str) -> Rubric:
    criteria = [
        Criterion(
            criterion_id="EL1",
            name="Setup and apparatus",
            description="Assess whether the lab report clearly states apparatus, connections, and setup/procedure.",
            max_score=20.0,
            weight=0.20,
            required_modalities=["text", "diagram"],
            artifact_scope=["report", "design_diagram", "image"],
            evaluation_dimensions=["completeness", "clarity"],
            evaluator_hints=["lab_setup_completeness", "diagram_completeness"],
            integrity_policy="review_only",
            integrity_scope="text",
            aspects=[
                CriterionAspect("apparatus_listed", "Instruments/components are identified.", True, ["text"], ["paragraph"], ["apparatus", "instrument"], 1),
                CriterionAspect("setup_described", "Connection/setup is described or drawn.", True, ["text", "diagram"], ["paragraph", "design_diagram"], ["setup", "connection"], 1),
            ],
            metadata={"instrument_terms": ["oscilloscope", "cro", "dso", "multimeter", "function generator", "power supply"], "setup_terms": ["apparatus", "setup", "connection", "procedure", "measure"]},
        ),
        Criterion(
            criterion_id="EL2",
            name="Observation table and measurements",
            description="Assess whether measured readings are presented clearly with sufficient detail and units.",
            max_score=20.0,
            weight=0.20,
            required_modalities=["table", "text"],
            artifact_scope=["spreadsheet", "report", "image"],
            evaluation_dimensions=["evidence_quality", "completeness"],
            evaluator_hints=["observation_table_quality", "simulation_evidence"],
            aspects=[
                CriterionAspect("table_present", "Observation table or readings are present.", True, ["table"], ["csv_table"], ["observation"], 1),
                CriterionAspect("units_present", "Measured values indicate units or quantities.", True, ["table", "text"], ["csv_table", "paragraph"], ["unit", "volt", "ampere", "hertz"], 1),
            ],
            integrity_policy="review_only",
            integrity_scope="text",
        ),
        Criterion(
            criterion_id="EL3",
            name="Calculations and derived results",
            description="Assess whether formula-based calculations and derived values are shown correctly.",
            max_score=20.0,
            weight=0.20,
            required_modalities=["text", "equation"],
            artifact_scope=["report", "image", "text"],
            evaluation_dimensions=["correctness", "justification"],
            evaluator_hints=["calculation_correctness", "technical_correctness"],
            aspects=[
                CriterionAspect("formula_used", "Relevant formula or relation is shown.", True, ["text", "equation"], ["paragraph", "math_ocr"], ["formula", "equation"], 1),
                CriterionAspect("steps_shown", "Calculation steps or substitutions are shown.", True, ["text", "equation"], ["paragraph", "math_ocr"], ["substituting", "therefore", "calculation"], 1),
            ],
            integrity_policy="review_only",
            integrity_scope="text",
        ),
        Criterion(
            criterion_id="EL4",
            name="Measured versus expected behavior",
            description="Assess whether the report compares measured observations with expected/theoretical behavior.",
            max_score=25.0,
            weight=0.25,
            required_modalities=["text", "table"],
            artifact_scope=["report", "spreadsheet", "text"],
            evaluation_dimensions=["consistency", "interpretation"],
            evaluator_hints=["measured_expected_alignment", "result_analysis", "cross_modal_consistency"],
            cross_checks=["claims_match_figures"],
            aspects=[
                CriterionAspect("comparison_present", "Measured and expected/theoretical behavior are compared.", True, ["text", "table"], ["paragraph", "csv_table"], ["expected", "measured", "deviation"], 1),
                CriterionAspect("metric_alignment", "Key metrics/observations relevant to the experiment are discussed.", True, ["text", "table"], ["paragraph", "csv_table"], ["gain", "voltage", "current", "frequency", "cutoff"], 1),
            ],
            metadata={"expected_metrics": ["voltage", "current", "frequency", "gain"], "expected_terms": ["expected", "theoretical", "measured", "deviation"]},
            integrity_policy="discount_if_relevant",
            integrity_scope="text",
        ),
        Criterion(
            criterion_id="EL5",
            name="Error analysis and precautions",
            description="Assess whether sources of error, precautions, or simulation-hardware differences are discussed.",
            max_score=15.0,
            weight=0.15,
            required_modalities=["text"],
            artifact_scope=["report", "text"],
            evaluation_dimensions=["reflection", "technical_depth"],
            evaluator_hints=["error_analysis_quality", "simulation_hardware_alignment"],
            aspects=[
                CriterionAspect("error_sources", "Likely error sources or deviations are discussed.", True, ["text"], ["paragraph"], ["error", "deviation", "tolerance"], 1),
                CriterionAspect("precautions", "Precautions or mitigation ideas are given.", False, ["text"], ["paragraph"], ["precaution", "avoid", "calibrate"], 1),
            ],
            metadata={"llm_weight": 0.15},
            integrity_policy="review_only",
            integrity_scope="text",
        ),
    ]
    return Rubric(assignment_id=assignment_id, assignment_title=assignment_title, required_artifacts=["report"], criteria=criteria)


def electronics_experiment_template(assignment_id: str, assignment_title: str) -> Rubric:
    rubric = ee_lab_report_template(assignment_id, assignment_title)
    rubric.assignment_title = assignment_title
    rubric.criteria[3].metadata.update({"expected_metrics": ["gain", "cutoff", "bandwidth", "voltage"], "expected_terms": ["simulation", "theoretical", "measured", "hardware", "deviation"]})
    rubric.criteria[4].description = "Assess whether the submission discusses error sources, precautions, and simulation-versus-hardware differences where relevant."
    return rubric
