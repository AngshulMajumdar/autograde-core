from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from autograde.rubric import Rubric
from autograde.subjects.base import SubjectProfileMetadata
from autograde.subjects.communication_vlsi_labs import rubric_templates


@dataclass(slots=True)
class CommunicationVLSILabsProfile:
    metadata: SubjectProfileMetadata = field(default_factory=lambda: SubjectProfileMetadata(
        subject_id="communication_vlsi_labs",
        display_name="Communication / VLSI Labs",
        supported_modalities=["text", "code", "table", "diagram", "image", "plot"],
        recommended_assignment_types=["communication_lab", "vlsi_lab"],
        notes="Profile for communication and VLSI labs with waveforms, timing diagrams, HDL, and simulated/observed behavior.",
    ))

    def available_templates(self) -> List[str]:
        return ["communication_lab", "vlsi_lab"]

    def build_rubric(self, template_id: str, assignment_id: str, assignment_title: str) -> Rubric:
        if template_id == "communication_lab":
            return rubric_templates.communication_lab_template(assignment_id, assignment_title)
        if template_id == "vlsi_lab":
            return rubric_templates.vlsi_lab_template(assignment_id, assignment_title)
        raise ValueError(f"Unknown communication/VLSI template: {template_id}")

    def default_integrity_modes(self) -> Dict[str, str]:
        return {
            "external_text": "review_only",
            "intra_cohort_text": "review_only",
            "intra_cohort_code": "review_only",
        }
