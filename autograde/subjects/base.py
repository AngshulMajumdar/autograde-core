from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Protocol

from autograde.rubric import Rubric


@dataclass(slots=True)
class SubjectProfileMetadata:
    subject_id: str
    display_name: str
    supported_modalities: List[str] = field(default_factory=list)
    recommended_assignment_types: List[str] = field(default_factory=list)
    notes: str = ""


class SubjectProfile(Protocol):
    metadata: SubjectProfileMetadata

    def available_templates(self) -> List[str]: ...

    def build_rubric(self, template_id: str, assignment_id: str, assignment_title: str) -> Rubric: ...

    def default_integrity_modes(self) -> Dict[str, str]: ...
