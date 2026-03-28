from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from autograde.rubric import Rubric
from autograde.subjects.base import SubjectProfileMetadata
from autograde.subjects.lab_science import rubric_templates


@dataclass(slots=True)
class LabScienceProfile:
    metadata: SubjectProfileMetadata = field(default_factory=lambda: SubjectProfileMetadata(
        subject_id="lab_science",
        display_name="Lab Science / Experimental Report",
        supported_modalities=["text", "table", "image", "diagram", "citation"],
        recommended_assignment_types=["lab_report", "experimental_project"],
        notes=(
            "Lab-science profile for methodology, observations, results, interpretation, and limitation-aware grading. "
            "Best for experiments reported through prose plus tables/plots rather than raw instrument integration."
        ),
    ))

    def available_templates(self) -> List[str]:
        return ["lab_report", "experimental_project"]

    def build_rubric(self, template_id: str, assignment_id: str, assignment_title: str) -> Rubric:
        if template_id == "lab_report":
            return rubric_templates.lab_report_template(assignment_id, assignment_title)
        if template_id == "experimental_project":
            return rubric_templates.experimental_project_template(assignment_id, assignment_title)
        raise ValueError(f"Unknown lab-science template: {template_id}")

    def default_integrity_modes(self) -> Dict[str, str]:
        return {
            "external_text": "review_only",
            "intra_cohort_text": "review_only",
        }
