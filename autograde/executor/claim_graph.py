from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean
from typing import Dict, Iterable, List, Sequence

from autograde.executor.claims import Claim, ClaimExtractor
from autograde.executor.normalization import ClaimNormalizer
from autograde.models import EvidenceObject


@dataclass(slots=True)
class ClaimNode:
    claim_id: str
    claim_type: str
    subject: str
    value: str | float
    evidence_id: str
    confidence: float
    raw_text: str
    tags: List[str] = field(default_factory=list)
    canonical_subject: str | None = None


@dataclass(slots=True)
class ClaimEdge:
    source_claim_id: str
    target_claim_id: str
    relation: str
    confidence: float


@dataclass(slots=True)
class ClaimGraph:
    submission_id: str
    nodes: List[ClaimNode] = field(default_factory=list)
    edges: List[ClaimEdge] = field(default_factory=list)
    evidence_to_claim_ids: Dict[str, List[str]] = field(default_factory=dict)

    def claims_for_evidence_ids(self, evidence_ids: Sequence[str]) -> List[ClaimNode]:
        wanted = set(evidence_ids)
        return [node for node in self.nodes if node.evidence_id in wanted]

    def summary(self) -> Dict[str, object]:
        by_type: Dict[str, int] = {}
        for node in self.nodes:
            by_type[node.claim_type] = by_type.get(node.claim_type, 0) + 1
        confidences = [n.confidence for n in self.nodes]
        avg_confidence = round(mean(confidences), 3) if confidences else 0.0
        return {
            "claim_count": len(self.nodes),
            "edge_count": len(self.edges),
            "claim_types": by_type,
            "avg_confidence": avg_confidence,
        }


class ClaimGraphBuilder:
    def __init__(self) -> None:
        self.extractor = ClaimExtractor()
        self.normalizer = ClaimNormalizer()

    def build(self, submission_id: str, evidence: Sequence[EvidenceObject]) -> ClaimGraph:
        raw_claims = self.extractor.extract(evidence)
        graph = ClaimGraph(submission_id=submission_id)
        claim_nodes: List[ClaimNode] = []
        key_to_claim_id: Dict[tuple[str, str, str, str], str] = {}

        for idx, claim in enumerate(raw_claims, start=1):
            canonical_subject, canonical_value = self.normalizer.normalize_claim(claim.claim_type, claim.subject, claim.value, claim.raw_text)
            key = (claim.claim_type, canonical_subject, str(canonical_value), claim.evidence_id)
            if key in key_to_claim_id:
                continue
            node = ClaimNode(
                claim_id=f"cl_{idx:04d}",
                claim_type=claim.claim_type,
                subject=canonical_subject,
                value=canonical_value,
                evidence_id=claim.evidence_id,
                confidence=claim.confidence,
                raw_text=claim.raw_text,
                tags=self._infer_tags(claim),
                canonical_subject=self.normalizer.normalize_claim(claim.claim_type, claim.subject, claim.value, claim.raw_text)[0],
            )
            key_to_claim_id[key] = node.claim_id
            claim_nodes.append(node)
            graph.evidence_to_claim_ids.setdefault(node.evidence_id, []).append(node.claim_id)

        graph.nodes = claim_nodes
        graph.edges = self._build_edges(claim_nodes)
        return graph

    @staticmethod
    def _infer_tags(claim: Claim) -> List[str]:
        tags = [claim.claim_type]
        if claim.subject:
            tags.append(f"subject:{claim.subject}")
        if claim.claim_type.endswith('_claim'):
            tags.append('assertion')
        if claim.claim_type.endswith('_fact'):
            tags.append('observation')
        return tags

    @staticmethod
    def _build_edges(nodes: Sequence[ClaimNode]) -> List[ClaimEdge]:
        edges: List[ClaimEdge] = []
        for i, src in enumerate(nodes):
            for dst in nodes[i + 1:]:
                if src.evidence_id == dst.evidence_id:
                    continue
                if src.subject != dst.subject:
                    continue
                relation = None
                confidence = min(src.confidence, dst.confidence)
                if src.claim_type.endswith('_claim') and dst.claim_type.endswith('_fact'):
                    relation = 'supports_or_conflicts'
                elif src.claim_type.endswith('_fact') and dst.claim_type.endswith('_claim'):
                    relation = 'supports_or_conflicts'
                elif src.claim_type.endswith('_claim') and dst.claim_type.endswith('_claim'):
                    relation = 'co_claims'
                    confidence *= 0.9
                elif src.claim_type.endswith('_fact') and dst.claim_type.endswith('_fact'):
                    relation = 'co_facts'
                    confidence *= 0.85
                if relation:
                    edges.append(ClaimEdge(src.claim_id, dst.claim_id, relation, round(confidence, 3)))
        return edges
