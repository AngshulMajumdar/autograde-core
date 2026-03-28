from __future__ import annotations

from autograde.coverage.aspect_model import CriterionAspect
from autograde.rubric import Criterion, Rubric


def embedded_system_lab_template(assignment_id: str, assignment_title: str) -> Rubric:
    criteria = [
        Criterion(
            criterion_id="EM1",
            name="System functionality",
            description="Assess whether the hardware-software system appears to achieve the intended functionality.",
            max_score=30.0,
            weight=0.30,
            required_modalities=["code", "text"],
            evaluation_dimensions=["correctness", "consistency"],
            artifact_scope=["source_code", "report", "image"],
            evaluator_hints=["hardware_software_alignment", "implementation_report_alignment"],
            aspects=[
                CriterionAspect("functionality_claimed", "The intended functionality is stated.", True, ["text"], ["paragraph"], ["sensor", "actuator", "display", "motor", "control"], 1),
                CriterionAspect("code_present", "Implementation code is present.", True, ["code"], ["function"], ["setup", "loop", "main", "interrupt"], 1),
            ],
        ),
        Criterion(
            criterion_id="EM2",
            name="Peripheral configuration",
            description="Assess whether relevant peripherals and interfaces are configured plausibly.",
            max_score=20.0,
            weight=0.20,
            required_modalities=["code"],
            evaluation_dimensions=["correctness", "technical_depth"],
            artifact_scope=["source_code", "notebook"],
            evaluator_hints=["peripheral_configuration_correctness"],
        ),
        Criterion(
            criterion_id="EM3",
            name="Sensor/actuator behavior",
            description="Assess whether the observed behavior of sensors/actuators is documented and plausible.",
            max_score=20.0,
            weight=0.20,
            required_modalities=["text", "code"],
            evaluation_dimensions=["consistency", "correctness"],
            artifact_scope=["report", "source_code", "image"],
            evaluator_hints=["sensor_actuator_behavior", "behavioral_correctness"],
        ),
        Criterion(
            criterion_id="EM4",
            name="Runtime or log evidence",
            description="Assess whether logs/serial output/state behavior support the claimed functionality.",
            max_score=15.0,
            weight=0.15,
            required_modalities=["text"],
            evaluation_dimensions=["clarity", "justification"],
            artifact_scope=["report", "image", "text"],
            evaluator_hints=["serial_log_behavior_alignment", "state_machine_behavior"],
        ),
        Criterion(
            criterion_id="EM5",
            name="Report-code consistency",
            description="Assess whether the report aligns with the implementation and observed behavior.",
            max_score=15.0,
            weight=0.15,
            required_modalities=["text", "code"],
            evaluation_dimensions=["consistency", "correctness"],
            artifact_scope=["report", "source_code"],
            evaluator_hints=["implementation_report_alignment"],
            metadata={"llm_weight": 0.15},
        ),
    ]
    return Rubric(assignment_id=assignment_id, assignment_title=assignment_title, required_artifacts=["report"], criteria=criteria)
