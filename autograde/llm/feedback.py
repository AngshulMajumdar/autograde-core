from __future__ import annotations

from autograde.llm.client import get_default_llm_client
from autograde.llm.prompt_builder import build_feedback_prompt
from autograde.llm.schemas import LLMRequest
from autograde.models import GradingResult


class LLMFeedbackGenerator:
    def __init__(self) -> None:
        self.client = get_default_llm_client()

    def generate(self, result: GradingResult) -> dict[str, object]:
        prompt = build_feedback_prompt(result)
        feedback = self.client.generate_feedback(
            LLMRequest(
                evaluator_id='llm_feedback_generator',
                criterion_id='feedback',
                prompt=prompt,
                evidence_refs=[cr.criterion_id for cr in result.criterion_results[:8]],
                metadata={'submission_id': result.submission_id},
            )
        )
        return {
            'summary': feedback.summary,
            'strengths': feedback.strengths,
            'weaknesses': feedback.weaknesses,
            'suggestions': feedback.suggestions,
            'provider': feedback.raw.get('provider', 'unknown'),
        }
