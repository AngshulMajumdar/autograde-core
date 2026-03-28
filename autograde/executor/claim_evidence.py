from __future__ import annotations

from dataclasses import dataclass, field
from math import isclose
from typing import Any, Dict, Iterable, List, Sequence

from autograde.executor.claim_graph import ClaimGraph, ClaimNode
from autograde.executor.evidence_query import EvidenceBundle
from autograde.rubric import Criterion


@dataclass(slots=True)
class ClaimEvidenceLink:
    claim_id: str
    subject: str
    claim_type: str
    claim_value: Any
    supporting_claim_ids: List[str] = field(default_factory=list)
    contradicting_claim_ids: List[str] = field(default_factory=list)
    support_status: str = "unsupported"  # supported | weakly_supported | unsupported | contradicted
    confidence: float = 0.0
    rationale: str = ""
    evidence_ids: List[str] = field(default_factory=list)


@dataclass(slots=True)
class ClaimEvidenceAssessment:
    overall_status: str = "not_applicable"  # supported | mixed | unsupported | contradicted | not_applicable
    support_ratio: float = 0.0
    contradicted_ratio: float = 0.0
    links: List[ClaimEvidenceLink] = field(default_factory=list)
    flags: List[Dict[str, Any]] = field(default_factory=list)
    rationale: str = ""
    confidence_multiplier: float = 1.0
    score_multiplier: float = 1.0
    escalate: bool = False


class ClaimEvidenceReasoner:
    """Reasons over extracted claims and observed facts across submission artifacts.

    The goal is not full symbolic semantics. It links report/code/table/plot/diagram claims to
    supporting or contradicting facts and feeds that into criterion decisions.
    """

    def assess(
        self,
        criterion: Criterion,
        evidence_bundle: EvidenceBundle,
        claim_graph: ClaimGraph | None = None,
    ) -> ClaimEvidenceAssessment:
        if claim_graph is None:
            return ClaimEvidenceAssessment(rationale="No claim graph was available for claim–evidence reasoning.")

        bundle_evidence_ids = set(evidence_bundle.direct_ids) | set(evidence_bundle.supporting_ids)
        bundle_nodes = claim_graph.claims_for_evidence_ids(sorted(bundle_evidence_ids))
        claim_nodes = [n for n in bundle_nodes if n.claim_type.endswith("_claim")]
        if not claim_nodes:
            return ClaimEvidenceAssessment(
                overall_status="not_applicable",
                rationale="No explicit claims were present in the criterion evidence bundle.",
            )

        all_nodes = list(claim_graph.nodes)
        links: List[ClaimEvidenceLink] = []
        supported = contradicted = 0
        flags: List[Dict[str, Any]] = []

        for claim in claim_nodes:
            support_nodes = [n for n in all_nodes if n.claim_id != claim.claim_id and self._supports(claim, n)]
            contradiction_nodes = [n for n in all_nodes if n.claim_id != claim.claim_id and self._contradicts(claim, n)]

            if contradiction_nodes:
                status = "contradicted"
                contradicted += 1
                confidence = round(max(0.2, min([n.confidence for n in contradiction_nodes] + [claim.confidence])) * 0.9, 3)
                rationale = f"Claim '{claim.subject}' is contradicted by observed evidence in other artifacts."
                flags.append({
                    "type": "claim_evidence_contradiction",
                    "severity": "high",
                    "claim_id": claim.claim_id,
                    "subject": claim.subject,
                })
            elif support_nodes:
                if any(n.evidence_id in bundle_evidence_ids for n in support_nodes):
                    status = "supported"
                    confidence = round(min(0.98, max([n.confidence for n in support_nodes] + [claim.confidence])), 3)
                    rationale = f"Claim '{claim.subject}' is supported by direct evidence in the submission."
                    supported += 1
                else:
                    status = "weakly_supported"
                    confidence = round(min(0.9, sum(n.confidence for n in support_nodes) / len(support_nodes) * 0.85), 3)
                    rationale = f"Claim '{claim.subject}' is only indirectly supported outside the criterion bundle."
                    supported += 1
            else:
                status = "unsupported"
                confidence = round(max(0.25, claim.confidence * 0.6), 3)
                rationale = f"Claim '{claim.subject}' is asserted without supporting evidence."
                flags.append({
                    "type": "unsupported_claim",
                    "severity": "medium",
                    "claim_id": claim.claim_id,
                    "subject": claim.subject,
                })

            evidence_ids = [claim.evidence_id] + [n.evidence_id for n in support_nodes] + [n.evidence_id for n in contradiction_nodes]
            links.append(
                ClaimEvidenceLink(
                    claim_id=claim.claim_id,
                    subject=claim.subject,
                    claim_type=claim.claim_type,
                    claim_value=claim.value,
                    supporting_claim_ids=[n.claim_id for n in support_nodes],
                    contradicting_claim_ids=[n.claim_id for n in contradiction_nodes],
                    support_status=status,
                    confidence=confidence,
                    rationale=rationale,
                    evidence_ids=sorted(set(evidence_ids)),
                )
            )

        total = len(claim_nodes)
        support_ratio = supported / total if total else 0.0
        contradicted_ratio = contradicted / total if total else 0.0

        overall_status = "supported"
        confidence_multiplier = 1.0
        score_multiplier = 1.0
        escalate = False
        rationale_parts: List[str] = []

        if contradicted_ratio > 0:
            overall_status = "contradicted"
            confidence_multiplier *= max(0.45, 1.0 - 0.55 * contradicted_ratio)
            score_multiplier *= max(0.4, 1.0 - 0.6 * contradicted_ratio)
            escalate = True
            rationale_parts.append(
                f"{contradicted}/{total} grading-relevant claims were contradicted by other evidence."
            )
        elif support_ratio >= 0.8:
            overall_status = "supported"
            rationale_parts.append(
                f"Most grading-relevant claims ({supported}/{total}) were supported by evidence."
            )
        elif support_ratio >= 0.4:
            overall_status = "mixed"
            confidence_multiplier *= 0.88
            score_multiplier *= 0.92
            rationale_parts.append(
                f"Only part of the grading-relevant claims ({supported}/{total}) were supported by evidence."
            )
        else:
            overall_status = "unsupported"
            confidence_multiplier *= 0.72
            score_multiplier *= 0.8
            rationale_parts.append(
                f"Most grading-relevant claims ({total - supported}/{total}) lacked supporting evidence."
            )

        return ClaimEvidenceAssessment(
            overall_status=overall_status,
            support_ratio=round(support_ratio, 3),
            contradicted_ratio=round(contradicted_ratio, 3),
            links=links,
            flags=flags,
            rationale=" ".join(rationale_parts) if rationale_parts else "Claim–evidence reasoning found no actionable issues.",
            confidence_multiplier=round(confidence_multiplier, 3),
            score_multiplier=round(score_multiplier, 3),
            escalate=escalate,
        )

    def _supports(self, claim: ClaimNode, other: ClaimNode) -> bool:
        if not other.claim_type.endswith("_fact"):
            return False
        if claim.subject != other.subject:
            return False
        return self._values_compatible(claim, other)

    def _contradicts(self, claim: ClaimNode, other: ClaimNode) -> bool:
        if not other.claim_type.endswith("_fact"):
            return False
        if claim.subject != other.subject:
            return False
        if self._values_compatible(claim, other):
            return False
        return self._same_semantic_space(claim, other)

    @staticmethod
    def _same_semantic_space(claim: ClaimNode, other: ClaimNode) -> bool:
        if claim.subject.startswith("accuracy") or claim.subject in {"accuracy", "precision", "recall", "f1", "error", "loss", "complexity", "algorithm", "feedback_loop", "data_structure"}:
            return True
        return type(claim.value) is type(other.value) or isinstance(claim.value, (int, float)) and isinstance(other.value, (int, float))

    def _values_compatible(self, claim: ClaimNode, other: ClaimNode) -> bool:
        claim_subject = claim.subject
        claim_value = claim.value
        other_value = other.value

        if claim.claim_type == "metric_threshold_claim":
            metric, _, op = claim_subject.partition(":")
            if metric != other.subject:
                return False
            return self._threshold_holds(op, claim_value, other_value)

        if isinstance(claim_value, (int, float)) and isinstance(other_value, (int, float)):
            return isclose(float(claim_value), float(other_value), rel_tol=0.08, abs_tol=0.02)

        return str(claim_value).strip().lower() == str(other_value).strip().lower()

    @staticmethod
    def _threshold_holds(op: str, threshold: Any, observed: Any) -> bool:
        try:
            thr = float(threshold)
            obs = float(observed)
        except (TypeError, ValueError):
            return False
        if op == ">":
            return obs >= thr
        if op == "<":
            return obs <= thr
        return False
