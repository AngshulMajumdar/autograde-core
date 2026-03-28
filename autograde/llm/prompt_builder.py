from __future__ import annotations

from typing import Sequence

from autograde.models import EvidenceObject, GradingResult
from autograde.rubric import Criterion


def _evidence_block(evidence: Sequence[EvidenceObject], limit: int = 6) -> str:
    blocks: list[str] = []
    for item in evidence[:limit]:
        snippet = (item.content or item.preview or '')[:900]
        structured = item.structured_content or {}
        blocks.append(
            f"- [{item.evidence_id}] modality={item.modality} subtype={item.subtype} location={item.location} structured={str(structured)[:240]} :: {snippet}"
        )
    return "\n".join(blocks)


def _criterion_context(criterion: Criterion) -> str:
    aspects = getattr(criterion, 'aspects', []) or []
    aspect_lines = [f"- {a.aspect_id}: required={a.required}, tags={a.tags}, modalities={a.modalities}" for a in aspects[:8]]
    metadata = criterion.metadata or {}
    meta_lines = []
    if metadata.get('expected_concepts'):
        for concept in metadata['expected_concepts'][:8]:
            meta_lines.append(
                f"- concept={concept.get('name')} required={concept.get('required', False)} synonyms={concept.get('synonyms', [])}"
            )
    if metadata.get('accepted_families'):
        meta_lines.append(f"- accepted_families={metadata.get('accepted_families')}")
    if metadata.get('expected_metrics'):
        meta_lines.append(f"- expected_metrics={metadata.get('expected_metrics')}")
    return (
        f"Criterion: {criterion.name}\n"
        f"Description: {criterion.description}\n"
        f"Evaluation dimensions: {', '.join(criterion.evaluation_dimensions)}\n"
        f"Required modalities: {criterion.required_modalities}\n"
        f"Criterion aspects:\n{chr(10).join(aspect_lines) or '- none'}\n"
        f"Criterion metadata hints:\n{chr(10).join(meta_lines) or '- none'}\n"
    )


def build_llm_prompt(kind: str, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> str:
    context = _criterion_context(criterion)
    evidence_text = _evidence_block(evidence)
    generic_json = (
        'Return only JSON with fields: score (0-1), confidence (0-1), rationale, '
        'evidence_refs (list of evidence ids actually used).'
    )
    specific = {
        'llm_subjective_reasoning': (
            "Judge whether the answer is actually responsive to the prompt, whether it covers the expected concepts, and whether the reasoning is justified rather than asserted. "
            "Penalize verbosity without substance. Reward concise but clearly supported answers."
        ),
        'llm_argument_quality': (
            "Judge thesis clarity, argumentative progression, qualification/counterargument handling, and whether evidence is integrated instead of merely mentioned. "
            "Distinguish a real interpretive position from generic summary. Reward direct engagement with expected concepts and penalize empty rhetorical polish."
        ),
        'llm_proof_explanation': (
            "Judge whether the proof explanation actually supports the claimed result. Look for explicit assumptions, justified inference steps, intermediate claims, and whether the conclusion is stronger than what the evidence proves. "
            "Do not accept fluent but unsupported proof language, and explicitly penalize missing key steps."
        ),
        'llm_design_justification': (
            "Judge whether the design explanation links components, constraints, expected behavior, and any simulation evidence. Allow alternative valid designs if the rationale and supporting evidence plausibly satisfy the target behavior. "
            "Do not require one canonical design, but do penalize vague claims of correctness without structural or behavioral support."
        ),
        'llm_feedback_synthesizer': (
            "Synthesize grounded feedback only from the criterion outcomes and evidence. Do not invent strengths or weaknesses not visible in the result data."
        ),
    }.get(kind, 'Evaluate only the provided evidence and remain conservative when evidence is weak.')
    return (
        f"{context}\n"
        f"Evidence:\n{evidence_text}\n\n"
        f"Instructions: {specific}\n"
        "Do not invent missing evidence. If evidence is weak, lower the score and confidence rather than assuming correctness.\n"
        f"{generic_json}"
    )


def build_claim_extraction_prompt(evidence: EvidenceObject) -> str:
    snippet = (evidence.content or evidence.preview or '')[:2200]
    structured = evidence.structured_content or {}
    return (
        f"Extract grading-relevant claims or facts from this evidence.\n"
        f"Modality: {evidence.modality}\nSubtype: {evidence.subtype}\n"
        f"Structured content: {structured}\n\n"
        f"Evidence text/content:\n{snippet}\n\n"
        "Return only claims that matter for grading, such as algorithm choice, metrics, thresholds, complexity, design behavior, methods, limitations, or conclusions. "
        "Drop weak or speculative claims rather than forcing extraction."
    )


def build_feedback_prompt(result: GradingResult) -> str:
    crit_lines = []
    for cr in result.criterion_results[:10]:
        crit_lines.append(
            f"- {cr.criterion_id}: score={cr.score}/{cr.max_score}, status={cr.status}, conf={cr.confidence}, coverage={cr.coverage_status}, rationale={cr.rationale[:240]}"
        )
    review_text = "\n".join(f"- {rb.get('criterion_id')}: {rb.get('reason')}" for rb in result.review_bundles[:8]) or '- none'
    return (
        f"Generate concise student-facing feedback for submission {result.submission_id}.\n"
        f"Final score: {result.final_score}/{result.max_score}\n\n"
        f"Criterion results:\n" + "\n".join(crit_lines) + "\n\n"
        + f"Review issues:\n{review_text}\n\n"
        + "Return a short summary, 2-5 strengths, 2-5 weaknesses, and 2-5 actionable suggestions. Stay grounded in the criterion outcomes and mention missing required components where relevant."
    )


def build_rubric_induction_prompt(past_cases, subject_profile: str) -> str:
    blocks = []
    for i, case in enumerate(past_cases, start=1):
        blocks.append(
            f"""Case {i}
Submission summary:
{case.submission_summary}

Instructor feedback:
{case.feedback}

Assigned score:
{case.score}
"""
        )
    joined = "\n\n".join(blocks)
    return f"""
You are inducing an instructor rubric from previously graded work.

Subject profile: {subject_profile}

Infer the smallest useful set of grading criteria that explains the scoring and feedback patterns.
Do not invent exotic criteria.
Prefer broad reusable criteria such as correctness, explanation, analysis, evidence, structure, originality, methodology, implementation, results, interpretation.

Return strict JSON:
{{
  "criteria": [
    {{
      "name": "correctness",
      "description": "What this criterion measures",
      "weight": 0.40,
      "evaluators": ["subjective_reasoning"]
    }}
  ]
}}

Constraints:
- weights must sum to about 1.0
- 3 to 6 criteria only
- criteria must be general enough to reuse
- evaluator names must be from:
  ["subjective_reasoning", "argument_quality", "proof_explanation", "design_justification", "behavioral_correctness", "implementation_report_alignment", "result_analysis", "text_quality", "argumentation", "technical_correctness", "requirements_coverage", "cross_modal_consistency", "citation_integrity", "subjective_answer_quality"]
- no markdown
- JSON only

Past graded cases:
{joined}
"""
