from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from autograde.rubric import Rubric
from autograde.subjects.base import SubjectProfileMetadata
from autograde.subjects.mathematics import rubric_templates


@dataclass(slots=True)
class MathematicsProfile:
    metadata: SubjectProfileMetadata = field(default_factory=lambda: SubjectProfileMetadata(
        subject_id="mathematics",
        display_name="Mathematics / Proof and Derivation",
        supported_modalities=["text", "equation", "image"],
        recommended_assignment_types=["proof", "derivation", "problem_set"],
        notes=(
            "Mathematics profile for proof-style and derivation-style submissions. Current version is text-centric and best for typed solutions, "
            "includes OCR-backed image support for handwritten or scanned proofs, but difficult handwriting still routes conservatively to review."
        ),
    ))

    def available_templates(self) -> List[str]:
        return ["proof", "derivation"]

    def build_rubric(self, template_id: str, assignment_id: str, assignment_title: str) -> Rubric:
        if template_id == "proof":
            return rubric_templates.proof_template(assignment_id, assignment_title)
        if template_id == "derivation":
            return rubric_templates.derivation_template(assignment_id, assignment_title)
        raise ValueError(f"Unknown mathematics template: {template_id}")

    def default_integrity_modes(self) -> Dict[str, str]:
        return {
            "external_text": "review_only",
            "intra_cohort_text": "review_only",
        }
