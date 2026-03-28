from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(slots=True)
class CriterionAspect:
    aspect_id: str
    description: str
    required: bool = True
    modalities: List[str] = field(default_factory=list)
    evidence_types: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    min_evidence_count: int = 1


@dataclass(slots=True)
class AspectCoverageResult:
    aspect_id: str
    status: str
    rationale: str
    evidence_ids: List[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass(slots=True)
class CoverageAssessment:
    overall_status: str
    coverage_score: float
    rationale: str
    aspect_results: List[AspectCoverageResult] = field(default_factory=list)
    missing_required: List[str] = field(default_factory=list)
    weak_required: List[str] = field(default_factory=list)
    flags: List[Dict[str, Any]] = field(default_factory=list)
