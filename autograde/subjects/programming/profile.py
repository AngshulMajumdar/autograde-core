from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from autograde.rubric import Rubric
from autograde.subjects.base import SubjectProfileMetadata
from autograde.subjects.programming import rubric_templates


@dataclass(slots=True)
class ProgrammingProfile:
    metadata: SubjectProfileMetadata = field(default_factory=lambda: SubjectProfileMetadata(
        subject_id="programming",
        display_name="Programming / Report + Code",
        supported_modalities=["text", "code", "execution", "table", "notebook"],
        recommended_assignment_types=["programming_project", "programming_lab", "report_code_assignment", "data_science_notebook"],
        notes="Strongest current profile: uses execution probes, report-code alignment, coverage checks, contradictions, and criterion-level integrity logic.",
    ))

    def available_templates(self) -> List[str]:
        return ["programming_project", "programming_lab", "data_science_notebook"]

    def build_rubric(self, template_id: str, assignment_id: str, assignment_title: str) -> Rubric:
        if template_id == "programming_project":
            return rubric_templates.programming_project_template(assignment_id, assignment_title)
        if template_id == "programming_lab":
            return rubric_templates.programming_lab_template(assignment_id, assignment_title)
        if template_id == "data_science_notebook":
            return rubric_templates.data_science_notebook_template(assignment_id, assignment_title)
        raise ValueError(f"Unknown programming template: {template_id}")

    def default_integrity_modes(self) -> Dict[str, str]:
        return {
            "external_text": "review_only",
            "external_code": "block_if_high",
            "intra_cohort_text": "discount_if_relevant",
            "intra_cohort_code": "block_if_high",
        }
