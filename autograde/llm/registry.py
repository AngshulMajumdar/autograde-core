from __future__ import annotations

from autograde.llm.evaluators import (
    LLMArgumentQualityEvaluator,
    LLMDesignJustificationEvaluator,
    LLMFeedbackSynthesizerEvaluator,
    LLMProofExplanationEvaluator,
    LLMSubjectiveReasoningEvaluator,
)


def llm_evaluators() -> dict[str, object]:
    return {
        "llm_subjective_reasoning": LLMSubjectiveReasoningEvaluator(),
        "llm_argument_quality": LLMArgumentQualityEvaluator(),
        "llm_proof_explanation": LLMProofExplanationEvaluator(),
        "llm_design_justification": LLMDesignJustificationEvaluator(),
        "llm_feedback_synthesizer": LLMFeedbackSynthesizerEvaluator(),
    }
