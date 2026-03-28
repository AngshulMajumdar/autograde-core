from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from autograde.rubric import Rubric
from autograde.subjects.base import SubjectProfileMetadata
from autograde.subjects.engineering import rubric_templates


@dataclass(slots=True)
class EngineeringProfile:
    metadata: SubjectProfileMetadata = field(default_factory=lambda: SubjectProfileMetadata(
        subject_id="engineering",
        display_name="Engineering / Circuit and System Design",
        supported_modalities=["diagram", "text", "table", "image"],
        recommended_assignment_types=["circuit_design", "system_design"],
        notes=(
            "Engineering profile grades diagrams by structural and functional constraints rather than exact template matching. "
            "It supports recognized valid families, simulation evidence, report-diagram alignment, and manual review for plausible unknown designs."
        ),
    ))

    def available_templates(self) -> List[str]:
        return ["circuit_design"]

    def build_rubric(self, template_id: str, assignment_id: str, assignment_title: str) -> Rubric:
        if template_id == "circuit_design":
            return rubric_templates.circuit_design_template(assignment_id, assignment_title)
        raise ValueError(f"Unknown engineering template: {template_id}")

    def default_integrity_modes(self) -> Dict[str, str]:
        return {
            "external_text": "review_only",
            "intra_cohort_text": "review_only",
            "external_design": "review_only",
            "intra_cohort_design": "review_only",
        }
