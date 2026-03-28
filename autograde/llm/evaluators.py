from __future__ import annotations

from typing import Sequence

from autograde.evaluators.base import BaseEvaluator
from autograde.llm.client import get_default_llm_client
from autograde.llm.prompt_builder import build_llm_prompt
from autograde.llm.schemas import LLMRequest
from autograde.models import EvidenceObject, EvaluatorResult
from autograde.rubric import Criterion


class BaseLLMEvaluator(BaseEvaluator):
    llm_kind = "llm_generic"
    evaluator_id = "llm_generic"

    def __init__(self) -> None:
        self.client = get_default_llm_client()

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        prompt = build_llm_prompt(self.evaluator_id, criterion, evidence)
        evidence_refs = [e.evidence_id for e in evidence[:8]]
        result = self.client.evaluate(
            LLMRequest(
                evaluator_id=self.evaluator_id,
                criterion_id=criterion.criterion_id,
                prompt=prompt,
                evidence_refs=evidence_refs,
                metadata={"criterion": criterion.name},
            )
        )
        provider = str(result.raw.get("provider", "unknown"))
        flags = [{"type": "llm_evaluation", "provider": provider, "live": self.client.is_live}]
        return EvaluatorResult(
            evaluator_id=self.evaluator_id,
            criterion_id=criterion.criterion_id,
            score=round(result.score * criterion.max_score, 2),
            max_score=criterion.max_score,
            confidence=result.confidence,
            rationale=result.rationale,
            supporting_evidence=result.evidence_refs,
            flags=flags,
        )


class LLMSubjectiveReasoningEvaluator(BaseLLMEvaluator):
    evaluator_id = "llm_subjective_reasoning"


class LLMArgumentQualityEvaluator(BaseLLMEvaluator):
    evaluator_id = "llm_argument_quality"


class LLMProofExplanationEvaluator(BaseLLMEvaluator):
    evaluator_id = "llm_proof_explanation"


class LLMDesignJustificationEvaluator(BaseLLMEvaluator):
    evaluator_id = "llm_design_justification"


class LLMFeedbackSynthesizerEvaluator(BaseLLMEvaluator):
    evaluator_id = "llm_feedback_synthesizer"
