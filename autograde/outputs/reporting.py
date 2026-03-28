from __future__ import annotations

from typing import List

from autograde.llm.feedback import LLMFeedbackGenerator
from autograde.models import GradingResult


class ReportFormatter:
    @staticmethod
    def student_feedback(result: GradingResult, use_llm: bool = False) -> str:
        if use_llm:
            feedback = LLMFeedbackGenerator().generate(result)
            lines = [
                f"Submission: {result.submission_id}",
                f"Final score: {result.final_score}/{result.max_score}",
                '',
                feedback.get('summary', ''),
                '',
                'Strengths:',
            ]
            lines.extend(f"- {item}" for item in feedback.get('strengths', []))
            lines.append('')
            lines.append('Weaknesses:')
            lines.extend(f"- {item}" for item in feedback.get('weaknesses', []))
            lines.append('')
            lines.append('Suggestions:')
            lines.extend(f"- {item}" for item in feedback.get('suggestions', []))
            return "\n".join(lines)
        lines: List[str] = [f"Submission: {result.submission_id}", f"Final score: {result.final_score}/{result.max_score}", '']
        for criterion in result.criterion_results:
            lines.append(f"- {criterion.criterion_id}: {criterion.score}/{criterion.max_score} (conf={criterion.confidence})")
            lines.append(f"  {criterion.rationale}")
        if result.review_flags:
            lines.append('')
            lines.append('Review flags:')
            for flag in result.review_flags:
                lines.append(f"  - {flag}")
        return "\n".join(lines)
