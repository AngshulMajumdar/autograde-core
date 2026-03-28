from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from autograde.rubric import Rubric
from autograde.subjects.base import SubjectProfileMetadata
from autograde.subjects.embedded_systems_labs import rubric_templates


@dataclass(slots=True)
class EmbeddedSystemsLabsProfile:
    metadata: SubjectProfileMetadata = field(default_factory=lambda: SubjectProfileMetadata(
        subject_id="embedded_systems_labs",
        display_name="Embedded Systems Labs",
        supported_modalities=["text", "code", "image", "table", "execution"],
        recommended_assignment_types=["embedded_system_lab"],
        notes="Profile for hardware-software integration labs using code, logs/screenshots, setup notes, and observed runtime behavior.",
    ))

    def available_templates(self) -> List[str]:
        return ["embedded_system_lab"]

    def build_rubric(self, template_id: str, assignment_id: str, assignment_title: str) -> Rubric:
        if template_id == "embedded_system_lab":
            return rubric_templates.embedded_system_lab_template(assignment_id, assignment_title)
        raise ValueError(f"Unknown embedded-systems template: {template_id}")

    def default_integrity_modes(self) -> Dict[str, str]:
        return {
            "external_text": "review_only",
            "intra_cohort_text": "review_only",
            "intra_cohort_code": "review_only",
        }
