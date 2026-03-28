from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(slots=True)
class LLMRequest:
    evaluator_id: str
    criterion_id: str
    prompt: str
    evidence_refs: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LLMEvaluation:
    evaluator_id: str
    score: float
    confidence: float
    rationale: str
    evidence_refs: List[str] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LLMClaimItem:
    claim_type: str
    subject: str
    value: str
    confidence: float
    raw_text: str


@dataclass(slots=True)
class LLMClaimExtraction:
    claims: List[LLMClaimItem] = field(default_factory=list)
    rationale: str = ''
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LLMFeedback:
    summary: str
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)
