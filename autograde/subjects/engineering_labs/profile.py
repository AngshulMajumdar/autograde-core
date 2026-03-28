from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from autograde.rubric import Rubric
from autograde.subjects.base import SubjectProfileMetadata
from autograde.subjects.engineering_labs import rubric_templates


@dataclass(slots=True)
class EngineeringLabsProfile:
    metadata: SubjectProfileMetadata = field(default_factory=lambda: SubjectProfileMetadata(
        subject_id="engineering_labs",
        display_name="Electrical / Electronics Engineering Labs",
        supported_modalities=["text", "table", "diagram", "image", "equation"],
        recommended_assignment_types=["ee_lab_report", "electronics_experiment"],
        notes=(
            "Profile for electrical/electronics lab submissions with setup, observation tables, calculations, measured-vs-expected analysis, and simulation-vs-hardware comparison."
        ),
    ))

    def available_templates(self) -> List[str]:
        return ["ee_lab_report", "electronics_experiment"]

    def build_rubric(self, template_id: str, assignment_id: str, assignment_title: str) -> Rubric:
        if template_id == "ee_lab_report":
            return rubric_templates.ee_lab_report_template(assignment_id, assignment_title)
        if template_id == "electronics_experiment":
            return rubric_templates.electronics_experiment_template(assignment_id, assignment_title)
        raise ValueError(f"Unknown engineering-labs template: {template_id}")

    def default_integrity_modes(self) -> Dict[str, str]:
        return {
            "external_text": "review_only",
            "intra_cohort_text": "review_only",
            "intra_cohort_code": "review_only",
        }
