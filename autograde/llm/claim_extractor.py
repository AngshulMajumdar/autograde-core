from __future__ import annotations

from typing import Sequence

from autograde.executor.normalization import ClaimNormalizer
from autograde.llm.client import MockLLMProvider, get_default_llm_client
from autograde.llm.prompt_builder import build_claim_extraction_prompt
from autograde.llm.schemas import LLMRequest
from autograde.models import EvidenceObject


class LLMClaimExtractor:
    def __init__(self) -> None:
        self.client = get_default_llm_client()
        self.normalizer = ClaimNormalizer()

    @property
    def is_live(self) -> bool:
        return not isinstance(getattr(self.client, 'provider', None), MockLLMProvider)

    def extract(self, evidence: Sequence[EvidenceObject]) -> tuple[list[dict[str, object]], bool]:
        claims: list[dict[str, object]] = []
        live_provider_used = self.is_live
        if not live_provider_used:
            return claims, False
        for ev in evidence:
            if ev.modality not in {'text', 'code', 'table', 'diagram', 'image'}:
                continue
            prompt = build_claim_extraction_prompt(ev)
            extraction = self.client.extract_claims(
                LLMRequest(
                    evaluator_id='llm_claim_extractor',
                    criterion_id='claim_extraction',
                    prompt=prompt,
                    evidence_refs=[ev.evidence_id],
                    metadata={'modality': ev.modality, 'subtype': ev.subtype},
                )
            )
            for item in extraction.claims:
                subj, val = self.normalizer.normalize_claim(item.claim_type, item.subject, item.value, item.raw_text)
                if item.confidence < 0.65:
                    continue
                claims.append({
                    'claim_type': item.claim_type,
                    'subject': subj,
                    'value': val,
                    'evidence_id': ev.evidence_id,
                    'confidence': item.confidence,
                    'raw_text': item.raw_text,
                    'source': 'llm',
                })
        return claims, live_provider_used
