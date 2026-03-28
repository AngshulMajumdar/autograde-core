#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autograde.llm.client import get_default_llm_client  # noqa: E402
from autograde.llm.schemas import LLMRequest  # noqa: E402


def _render_prompt(title: str, criterion_name: str, description: str, evidence: list[dict[str, str]], focus: str) -> str:
    blocks = []
    for item in evidence:
        snippet = item["content"][:900]
        blocks.append(f"- [{item['evidence_id']}] modality={item['modality']} subtype={item['subtype']} :: {snippet}")
    evidence_text = "\n".join(blocks)
    return (
        f"Case title: {title}\n"
        f"Criterion: {criterion_name}\n"
        f"Description: {description}\n\n"
        f"Evidence:\n{evidence_text}\n\n"
        "Return JSON only with keys score, confidence, rationale, evidence_refs. "
        "Do not invent missing evidence. Score should be normalized between 0 and 1.\n\n"
        f"Focus: {focus}"
    )


def build_cases() -> list[dict[str, object]]:
    return [
        {
            "label": "humanities",
            "evaluator_id": "llm_argument_quality",
            "criterion_id": "H_SMOKE",
            "prompt": _render_prompt(
                "Humanities argument smoke test",
                "Argument quality",
                "Assess whether the student makes a clear argument supported by reasons and evidence.",
                [
                    {
                        "evidence_id": "ev_h_1",
                        "modality": "text",
                        "subtype": "essay",
                        "content": (
                            "Public transport subsidies are justified because congestion, pollution, and unequal access create social costs that "
                            "private fares alone do not address. However, blanket subsidies can be wasteful, so the strongest policy is targeted support "
                            "combined with service-quality standards."
                        ),
                    }
                ],
                "Focus on thesis clarity, qualification, and evidence-backed reasoning.",
            ),
            "evidence_refs": ["ev_h_1"],
        },
        {
            "label": "mathematics",
            "evaluator_id": "llm_proof_explanation",
            "criterion_id": "M_SMOKE",
            "prompt": _render_prompt(
                "Mathematics proof smoke test",
                "Proof explanation",
                "Assess whether the proof explanation plausibly justifies the claimed result.",
                [
                    {
                        "evidence_id": "ev_m_1",
                        "modality": "text",
                        "subtype": "proof",
                        "content": (
                            "Let x_n converge to L. Choose N so that |x_n - L| < 1 for all n >= N. Then for n >= N, |x_n| <= |L| + 1. "
                            "The finitely many earlier terms x_1, ..., x_{N-1} also have a maximum absolute value. Hence the whole sequence is bounded."
                        ),
                    }
                ],
                "Focus on proof idea clarity, step justification, and whether the argument reaches the claimed conclusion.",
            ),
            "evidence_refs": ["ev_m_1"],
        },
        {
            "label": "engineering",
            "evaluator_id": "llm_design_justification",
            "criterion_id": "E_SMOKE",
            "prompt": _render_prompt(
                "Engineering design smoke test",
                "Design justification",
                "Assess whether the design rationale explains why the circuit should satisfy the requirements.",
                [
                    {
                        "evidence_id": "ev_e_1",
                        "modality": "text",
                        "subtype": "design_explanation",
                        "content": (
                            "The op-amp is used in a non-inverting configuration so the passband gain is approximately 1 + Rf/Rin = 2. "
                            "The RC network is placed in the feedback path so high-frequency components are attenuated, giving low-pass behavior."
                        ),
                    },
                    {
                        "evidence_id": "ev_e_2",
                        "modality": "diagram",
                        "subtype": "circuit",
                        "content": "non-inverting op-amp with RC feedback and labeled output node",
                    },
                ],
                "Focus on whether the rationale plausibly connects the structure of the design to the stated required behavior.",
            ),
            "evidence_refs": ["ev_e_1", "ev_e_2"],
        },
        {
            "label": "subjective",
            "evaluator_id": "llm_subjective_reasoning",
            "criterion_id": "S_SMOKE",
            "prompt": _render_prompt(
                "Subjective reasoning smoke test",
                "Short-answer reasoning",
                "Assess correctness, depth, and whether the answer actually addresses the question.",
                [
                    {
                        "evidence_id": "ev_s_1",
                        "modality": "text",
                        "subtype": "short_answer",
                        "content": (
                            "Median-of-means is robust to outliers because it splits the sample into blocks, computes block means, and then uses the median of those means. "
                            "However, it can be less data-efficient than the ordinary mean when contamination is absent."
                        ),
                    }
                ],
                "Focus on correctness, depth, and whether the answer covers both benefits and limitations.",
            ),
            "evidence_refs": ["ev_s_1"],
        },
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test the configured LLM provider with a few structured grading prompts.")
    parser.add_argument("--allow-mock", action="store_true", help="Allow the script to proceed even if the provider falls back to the mock backend.")
    parser.add_argument("--json", action="store_true", help="Print the final result object as JSON.")
    args = parser.parse_args()

    client = get_default_llm_client()
    provider_name = client.provider.__class__.__name__
    if provider_name == "MockLLMProvider" and not args.allow_mock:
        print("No live LLM provider is configured or reachable. Set AUTOGRADE_LLM_PROVIDER and provider-specific variables, or rerun with --allow-mock.")
        print("Recommended local path: install Ollama, pull a model, then set AUTOGRADE_LLM_PROVIDER=ollama.")
        return 2

    results: list[dict[str, object]] = []
    for case in build_cases():
        evaluation = client.evaluate(
            LLMRequest(
                evaluator_id=str(case["evaluator_id"]),
                criterion_id=str(case["criterion_id"]),
                prompt=str(case["prompt"]),
                evidence_refs=list(case["evidence_refs"]),
            )
        )
        results.append(
            {
                "case": case["label"],
                "evaluator": case["evaluator_id"],
                "provider": evaluation.raw.get("provider", provider_name),
                "score": evaluation.score,
                "confidence": evaluation.confidence,
                "rationale": evaluation.rationale,
                "supporting_evidence": evaluation.evidence_refs,
            }
        )

    payload = {
        "provider_class": provider_name,
        "env_provider": os.getenv("AUTOGRADE_LLM_PROVIDER", "auto"),
        "results": results,
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"Provider class: {provider_name}")
        for item in results:
            print("-" * 72)
            print(f"Case: {item['case']} | Evaluator: {item['evaluator']} | Provider: {item['provider']}")
            print(f"Score: {item['score']} | Confidence: {item['confidence']}")
            print(f"Rationale: {item['rationale']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
