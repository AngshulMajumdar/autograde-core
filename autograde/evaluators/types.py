from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from autograde.evaluators.base import BaseEvaluator
from autograde.models import EvidenceObject, EvaluatorResult
from autograde.rubric import Criterion


@dataclass(slots=True)
class EvaluatorDescriptor:
    evaluator_id: str
    evaluator_type: str
    strategy: str
    heuristic: bool = False
    notes: str = ''


class DeterministicEvaluator(BaseEvaluator):
    evaluator_type = "deterministic"

    def __init__(self, evaluator_id: str, strategy: str, implementation: BaseEvaluator, *, heuristic: bool = False, notes: str = "") -> None:
        self.evaluator_id = evaluator_id
        self.strategy = strategy
        self.implementation = implementation
        self.heuristic = heuristic
        self.notes = notes

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        result = self.implementation.evaluate(criterion, evidence)
        result.evaluator_id = self.evaluator_id
        note = f"Deterministic strategy={self.strategy}."
        if self.heuristic:
            note += " Heuristic and conservative by design."
            result.flags.append({"type": "heuristic_evaluator", "strategy": self.strategy})
        if self.notes:
            note += f" {self.notes}"
        result.rationale = f"{note} {result.rationale}".strip()
        return result


class LLMEvaluator(BaseEvaluator):
    evaluator_type = "llm"

    def __init__(self, evaluator_id: str, strategy: str, implementation: BaseEvaluator, *, notes: str = "") -> None:
        self.evaluator_id = evaluator_id
        self.strategy = strategy
        self.implementation = implementation
        self.notes = notes

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        result = self.implementation.evaluate(criterion, evidence)
        result.evaluator_id = self.evaluator_id
        provider_live = any(f.get("type") == "llm_evaluation" and f.get("live") for f in result.flags)
        note = f"LLM strategy={self.strategy}. Structured output only; deterministic aggregation remains authoritative."
        if not provider_live:
            note += " Provider was not live; output should be treated as scaffolding or test-only."
            result.flags.append({"type": "mock_backed_llm", "strategy": self.strategy})
        if self.notes:
            note += f" {self.notes}"
        result.rationale = f"{note} {result.rationale}".strip()
        result.flags.append({"type": "llm_bounded", "strategy": self.strategy})
        return result


class HybridEvaluator(BaseEvaluator):
    evaluator_type = "hybrid"

    def __init__(self, evaluator_id: str, strategy: str, deterministic_impl: BaseEvaluator, llm_impl: BaseEvaluator, *, llm_weight: float = 0.25, notes: str = "", require_live_llm: bool = True) -> None:
        self.evaluator_id = evaluator_id
        self.strategy = strategy
        self.deterministic_impl = deterministic_impl
        self.llm_impl = llm_impl
        self.llm_weight = max(0.0, min(0.5, llm_weight))
        self.notes = notes
        self.require_live_llm = require_live_llm

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        det = self.deterministic_impl.evaluate(criterion, evidence)
        llm = self.llm_impl.evaluate(criterion, evidence)
        provider_live = any(f.get("type") == "llm_evaluation" and f.get("live") for f in llm.flags)
        effective_llm_weight = self.llm_weight
        fallback_reason = None
        if self.require_live_llm and not provider_live:
            effective_llm_weight = 0.0
            fallback_reason = "live_llm_unavailable"
        elif llm.confidence < 0.45:
            effective_llm_weight = min(effective_llm_weight, 0.1)
            fallback_reason = "low_llm_confidence"
        score = (1.0 - effective_llm_weight) * det.score + effective_llm_weight * llm.score
        confidence = min(0.95, (1.0 - effective_llm_weight) * det.confidence + effective_llm_weight * llm.confidence)
        supporting = list(dict.fromkeys([*det.supporting_evidence, *llm.supporting_evidence]))
        flags = list(det.flags) + list(llm.flags) + [{"type": "hybrid_evaluator", "strategy": self.strategy, "llm_weight": round(effective_llm_weight, 2), "configured_llm_weight": round(self.llm_weight, 2)}]
        note = f"Hybrid strategy={self.strategy}. Deterministic core blended with bounded LLM weight={effective_llm_weight:.2f}."
        if fallback_reason:
            flags.append({"type": "hybrid_llm_fallback", "reason": fallback_reason})
            if fallback_reason == "live_llm_unavailable":
                note += " Live LLM unavailable, so deterministic path remained authoritative."
            else:
                note += " LLM confidence was low, so LLM influence was reduced."
        if self.notes:
            note += f" {self.notes}"
        return EvaluatorResult(
            evaluator_id=self.evaluator_id,
            criterion_id=criterion.criterion_id,
            score=round(score, 2),
            max_score=criterion.max_score,
            confidence=round(confidence, 3),
            rationale=f"{note} Deterministic: {det.rationale} LLM: {llm.rationale}".strip(),
            supporting_evidence=supporting,
            flags=flags,
        )
