from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Sequence

from autograde.executor.evidence_query import EvidenceBundle
from autograde.rubric import Criterion

_SEVERITY_ORDER = {"low": 1, "medium": 2, "high": 3}


def _severity_value(s: str | None) -> int:
    return _SEVERITY_ORDER.get((s or "").lower(), 0)


@dataclass(slots=True)
class IntegrityAssessment:
    relevant_flags: list[Dict[str, Any]] = field(default_factory=list)
    confidence_multiplier: float = 1.0
    score_multiplier: float = 1.0
    escalate: bool = False
    rationale: str = ""
    flags: list[Dict[str, Any]] = field(default_factory=list)


class IntegrityPolicyRouter:
    def assess(
        self,
        criterion: Criterion,
        evidence_bundle: EvidenceBundle,
        integrity_flags: Sequence[Dict[str, Any]] | None = None,
    ) -> IntegrityAssessment:
        integrity_flags = list(integrity_flags or [])
        if not integrity_flags or criterion.integrity_policy == "ignore":
            return IntegrityAssessment(rationale="No integrity interaction affected this criterion.")

        relevant = []
        for flag in integrity_flags:
            rel = self._relevance(flag, criterion, evidence_bundle)
            if rel >= 0.45:
                copied = dict(flag)
                copied["criterion_relevance"] = round(rel, 3)
                relevant.append(copied)

        if not relevant:
            return IntegrityAssessment(rationale="Integrity flags were present for the submission but were not strongly relevant to this criterion.")

        max_sev = max(_severity_value(f.get("severity")) for f in relevant)
        threshold = _severity_value(criterion.integrity_severity_threshold)
        score_multiplier = 1.0
        confidence_multiplier = 1.0
        escalate = False
        rationale = [f"{len(relevant)} integrity flag(s) were relevant to this criterion."]
        out_flags = [{"type": "integrity_relevance", "count": len(relevant), "severity": max((f.get("severity", "low") for f in relevant), key=_severity_value)}]

        policy = criterion.integrity_policy
        if policy == "review_only":
            confidence_multiplier = 0.86 if max_sev >= threshold else 0.94
            escalate = max_sev >= threshold
            rationale.append("Policy is review-only, so confidence was reduced without automatic score discount.")
        elif policy == "discount_if_relevant":
            if max_sev >= threshold:
                score_multiplier = 0.8 if max_sev == 2 else 0.6
                confidence_multiplier = 0.8 if max_sev == 2 else 0.68
                escalate = max_sev >= 3
                rationale.append("Relevant integrity evidence crossed the severity threshold, so the criterion was discounted.")
            else:
                confidence_multiplier = 0.92
                rationale.append("Relevant integrity evidence was below the severity threshold, so only confidence was reduced.")
        elif policy == "block_if_high":
            if max_sev >= max(threshold, 3):
                score_multiplier = 0.0
                confidence_multiplier = 0.55
                escalate = True
                out_flags.append({"type": "integrity_block", "severity": "high"})
                rationale.append("High-severity integrity evidence triggered a blocking policy for this criterion.")
            elif max_sev >= threshold:
                score_multiplier = 0.75
                confidence_multiplier = 0.75
                escalate = True
                rationale.append("Sub-threshold blocking condition was not met, but the criterion was discounted and escalated.")
            else:
                confidence_multiplier = 0.9
                rationale.append("Integrity evidence was relevant but below the blocking threshold.")
        else:
            confidence_multiplier = 0.9
            rationale.append("Unknown integrity policy; using conservative confidence reduction only.")

        return IntegrityAssessment(
            relevant_flags=relevant,
            confidence_multiplier=confidence_multiplier,
            score_multiplier=score_multiplier,
            escalate=escalate,
            rationale=" ".join(rationale),
            flags=out_flags,
        )

    def _relevance(self, flag: Dict[str, Any], criterion: Criterion, evidence_bundle: EvidenceBundle) -> float:
        scope = criterion.integrity_scope
        direct_ids = set(evidence_bundle.direct_ids) | set(evidence_bundle.supporting_ids)
        evidence_hits = 0.0
        for key in ("evidence_id", "matched_text_evidence_a", "matched_text_evidence_b", "matched_code_evidence_a", "matched_code_evidence_b"):
            if flag.get(key) and flag.get(key) in direct_ids:
                evidence_hits = 1.0
                break

        ftype = str(flag.get("type", ""))
        if scope == "all":
            modality_rel = 1.0
        elif scope == "text":
            modality_rel = 1.0 if "text" in ftype else 0.2
        elif scope == "code":
            modality_rel = 1.0 if any(k in ftype for k in ("code", "cohort")) else 0.2
        else:
            req = set(criterion.required_modalities)
            if "text" in req or "citation" in req:
                if "text" in ftype:
                    modality_rel = 0.85
                elif "code" in ftype:
                    modality_rel = 0.15
                else:
                    modality_rel = 0.45
            elif {"code", "execution", "source_code"} & req:
                if "code" in ftype:
                    modality_rel = 0.85
                elif "text" in ftype:
                    modality_rel = 0.2
                else:
                    modality_rel = 0.5
            else:
                modality_rel = 0.5

        severity_bonus = 0.05 * _severity_value(flag.get("severity"))
        return min(1.0, max(evidence_hits, modality_rel) + severity_bonus)
