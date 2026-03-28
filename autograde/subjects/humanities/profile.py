from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from autograde.rubric import Rubric
from autograde.subjects.base import SubjectProfileMetadata
from autograde.subjects.humanities import rubric_templates


@dataclass(slots=True)
class HumanitiesProfile:
    metadata: SubjectProfileMetadata = field(default_factory=lambda: SubjectProfileMetadata(
        subject_id="humanities",
        display_name="Humanities / Subjective Answers",
        supported_modalities=["text", "citation"],
        recommended_assignment_types=["short_answer", "essay", "source_based_response"],
        notes=(
            "Subjective-answer profile with length-aware heuristics, argumentation checks, citation-aware grading, "
            "coverage aspects, and integrity policies tuned for prose-heavy assignments."
        ),
    ))

    def available_templates(self) -> List[str]:
        return ["short_answer", "essay"]

    def build_rubric(self, template_id: str, assignment_id: str, assignment_title: str) -> Rubric:
        if template_id == "short_answer":
            return rubric_templates.humanities_short_answer_template(assignment_id, assignment_title)
        if template_id == "essay":
            return rubric_templates.humanities_essay_template(assignment_id, assignment_title)
        raise ValueError(f"Unknown humanities template: {template_id}")

    def default_integrity_modes(self) -> Dict[str, str]:
        return {
            "external_text": "review_only",
            "intra_cohort_text": "review_only",
        }
