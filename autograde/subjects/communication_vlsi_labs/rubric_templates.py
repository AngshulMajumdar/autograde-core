from __future__ import annotations

from autograde.coverage.aspect_model import CriterionAspect
from autograde.rubric import Criterion, Rubric


def communication_lab_template(assignment_id: str, assignment_title: str) -> Rubric:
    criteria = [
        Criterion(
            criterion_id="CV1",
            name="Experiment behavior",
            description="Assess whether the communication experiment behavior is correctly obtained and compared with expectation.",
            max_score=30.0,
            weight=0.30,
            required_modalities=["text", "table"],
            evaluation_dimensions=["correctness", "interpretation"],
            artifact_scope=["report", "spreadsheet", "image"],
            evaluator_hints=["expected_vs_simulated_behavior", "spectrum_metric_alignment"],
            aspects=[
                CriterionAspect("metrics_present", "Relevant metrics like gain/SNR/bandwidth/BER are reported.", True, ["text", "table"], ["paragraph", "csv_table"], ["snr", "ber", "bandwidth", "gain", "frequency"], 1),
                CriterionAspect("comparison_present", "Expected and observed behavior are compared.", True, ["text"], ["paragraph"], ["expected", "measured", "observed", "deviation"], 1),
            ],
            metadata={"expected_metrics": ["snr", "ber", "bandwidth", "gain", "frequency"]},
        ),
        Criterion(
            criterion_id="CV2",
            name="Waveform or spectrum interpretation",
            description="Assess whether plots/waveforms/spectrum evidence is interpreted correctly.",
            max_score=25.0,
            weight=0.25,
            required_modalities=["text", "image"],
            evaluation_dimensions=["interpretation", "clarity"],
            artifact_scope=["report", "image"],
            evaluator_hints=["waveform_interpretation", "result_analysis"],
            aspects=[
                CriterionAspect("waveform_present", "Waveform/spectrum evidence is present.", True, ["image", "text"], ["plot", "ocr_text"], ["waveform", "spectrum"], 1),
                CriterionAspect("interpretation_present", "The observed waveform/spectrum is interpreted.", True, ["text"], ["paragraph"], ["frequency", "amplitude", "phase", "carrier"], 1),
            ],
        ),
        Criterion(
            criterion_id="CV3",
            name="Timing or logic correctness",
            description="Assess timing-diagram, truth-table, or logic behavior correctness where relevant.",
            max_score=25.0,
            weight=0.25,
            required_modalities=["text", "diagram"],
            evaluation_dimensions=["correctness", "consistency"],
            artifact_scope=["report", "design_diagram", "image"],
            evaluator_hints=["timing_diagram_correctness", "digital_truth_table_consistency"],
            aspects=[
                CriterionAspect("timing_logic_terms", "Timing, state, or logic behavior is documented.", True, ["text", "diagram"], ["paragraph", "design_diagram"], ["clock", "state", "truth table", "logic", "delay"], 1),
            ],
        ),
        Criterion(
            criterion_id="CV4",
            name="Technical explanation",
            description="Assess the quality of technical explanation and reasoning in the lab report.",
            max_score=20.0,
            weight=0.20,
            required_modalities=["text"],
            evaluation_dimensions=["clarity", "justification"],
            artifact_scope=["report"],
            evaluator_hints=["subjective_answer_quality"],
            metadata={"length_band": "medium", "expected_concepts": [{"name":"principle","terms":["principle"]},{"name":"result","terms":["result","observed"]},{"name":"deviation","terms":["deviation","error"]}]},
        ),
    ]
    return Rubric(assignment_id=assignment_id, assignment_title=assignment_title, required_artifacts=["report"], criteria=criteria)


def vlsi_lab_template(assignment_id: str, assignment_title: str) -> Rubric:
    criteria = [
        Criterion(
            criterion_id="VL1",
            name="HDL/design behavior",
            description="Assess whether HDL/design artifacts reflect the intended digital behavior.",
            max_score=30.0,
            weight=0.30,
            required_modalities=["code", "text"],
            evaluation_dimensions=["correctness", "consistency"],
            artifact_scope=["source_code", "report"],
            evaluator_hints=["hdl_behavior_consistency", "design_report_alignment"],
            aspects=[
                CriterionAspect("hdl_present", "HDL or digital design description is present.", True, ["code"], ["function"], ["module", "entity", "always", "assign"], 1),
                CriterionAspect("behavior_described", "Behavior/state/logic of the design is described.", True, ["text"], ["paragraph"], ["state", "output", "counter", "flip-flop", "fsm"], 1),
            ],
        ),
        Criterion(
            criterion_id="VL2",
            name="Timing and logic validation",
            description="Assess whether timing diagrams or truth/state tables support the design behavior.",
            max_score=25.0,
            weight=0.25,
            required_modalities=["text", "diagram"],
            evaluation_dimensions=["correctness", "consistency"],
            artifact_scope=["report", "design_diagram", "image"],
            evaluator_hints=["timing_diagram_correctness", "digital_truth_table_consistency"],
        ),
        Criterion(
            criterion_id="VL3",
            name="Expected versus simulated behavior",
            description="Assess whether simulation behavior is compared with expected logic/timing behavior.",
            max_score=25.0,
            weight=0.25,
            required_modalities=["text", "table"],
            evaluation_dimensions=["correctness", "interpretation"],
            artifact_scope=["report", "spreadsheet", "image"],
            evaluator_hints=["expected_vs_simulated_behavior", "simulation_consistency"],
            metadata={"expected_metrics": ["delay", "frequency", "power", "timing"]},
        ),
        Criterion(
            criterion_id="VL4",
            name="Technical explanation",
            description="Assess whether the report explains the HDL/design decisions and observed behavior clearly.",
            max_score=20.0,
            weight=0.20,
            required_modalities=["text"],
            evaluation_dimensions=["clarity", "justification"],
            artifact_scope=["report"],
            evaluator_hints=["subjective_answer_quality"],
            metadata={"length_band": "medium", "expected_concepts": [{"name":"timing","terms":["timing","delay"]},{"name":"logic","terms":["logic","state","truth table"]},{"name":"behavior","terms":["behavior","output"]}]},
        ),
    ]
    return Rubric(assignment_id=assignment_id, assignment_title=assignment_title, required_artifacts=["report"], criteria=criteria)
