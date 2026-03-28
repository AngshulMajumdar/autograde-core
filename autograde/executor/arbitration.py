from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean
from typing import Any, Dict, Sequence

from autograde.executor.contradiction_detector import ContradictionReport
from autograde.executor.cross_checks import CrossCheckResult
from autograde.executor.integrity_policy import IntegrityAssessment
from autograde.executor.claim_evidence import ClaimEvidenceAssessment
from autograde.models import EvaluatorResult
from autograde.rubric import Criterion


@dataclass(slots=True)
class ArbitrationResult:
    confidence: float
    rationale: str
    flags: list[Dict[str, Any]] = field(default_factory=list)
    escalate: bool = False
    score_multiplier: float = 1.0
    blocked: bool = False
    contradiction_penalty: float = 0.0


class ArbitrationPolicy:
    def __init__(self, mild_disagreement: float = 0.2, strong_disagreement: float = 0.45) -> None:
        self.mild_disagreement = mild_disagreement
        self.strong_disagreement = strong_disagreement
        self._severity_rank = {"none": 0, "low": 1, "medium": 2, "high": 3}

    def resolve(
        self,
        criterion: Criterion,
        evaluator_results: Sequence[EvaluatorResult],
        criterion_max_score: float,
        integrity_flags: Sequence[Dict[str, Any]] | None = None,
        cross_check_results: Sequence[CrossCheckResult] | None = None,
        contradiction_report: ContradictionReport | None = None,
        integrity_assessment: IntegrityAssessment | None = None,
        claim_evidence_assessment: ClaimEvidenceAssessment | None = None,
    ) -> ArbitrationResult:
        integrity_flags = list(integrity_flags or [])
        cross_check_results = list(cross_check_results or [])
        contradiction_report = contradiction_report or ContradictionReport()
        integrity_assessment = integrity_assessment or IntegrityAssessment()
        claim_evidence_assessment = claim_evidence_assessment or ClaimEvidenceAssessment()
        if not evaluator_results:
            return ArbitrationResult(confidence=0.0, rationale="No evaluator outputs were available.", escalate=True)

        scores = [r.score / criterion_max_score if criterion_max_score else 0.0 for r in evaluator_results]
        spread = max(scores) - min(scores) if len(scores) > 1 else 0.0
        base_conf = mean(r.confidence for r in evaluator_results)
        flags: list[Dict[str, Any]] = []
        rationale_parts = ["Evaluator outputs were mutually consistent."]
        escalate = False
        blocked = False
        score_multiplier = 1.0
        contradiction_penalty = 0.0

        if spread >= self.strong_disagreement:
            base_conf *= 0.55
            flags.append({"type": "evaluator_disagreement", "severity": "high", "spread": round(spread, 3)})
            rationale_parts = ["Evaluator outputs strongly disagreed."]
            escalate = True
        elif spread >= self.mild_disagreement:
            base_conf *= 0.8
            flags.append({"type": "evaluator_disagreement", "severity": "medium", "spread": round(spread, 3)})
            rationale_parts = ["Evaluator outputs showed moderate disagreement."]

        failed_checks = [c for c in cross_check_results if not c.passed]
        if failed_checks:
            flags.extend(flag for c in failed_checks for flag in c.flags)
            if criterion.cross_check_policy == "binding":
                score_multiplier *= 0.6
                base_conf *= 0.75
                escalate = True
                rationale_parts.append("A binding cross-check failed, so the criterion score was discounted and escalated.")
            else:
                score_multiplier *= 0.9
                base_conf *= 0.9
                rationale_parts.append("An advisory cross-check failed, so confidence was reduced.")

        if contradiction_report.contradictions:
            c_mult, c_conf, c_escalate, c_blocked, c_penalty, c_reason = self._apply_contradiction_policy(
                criterion, contradiction_report
            )
            flags.extend(contradiction_report.flags)
            score_multiplier *= c_mult
            contradiction_penalty = c_penalty
            base_conf *= c_conf
            escalate = escalate or c_escalate
            blocked = blocked or c_blocked
            rationale_parts.append(c_reason)

        if claim_evidence_assessment.links:
            base_conf *= claim_evidence_assessment.confidence_multiplier
            score_multiplier *= claim_evidence_assessment.score_multiplier
            flags.extend(claim_evidence_assessment.flags)
            rationale_parts.append(claim_evidence_assessment.rationale)
            escalate = escalate or claim_evidence_assessment.escalate

        if integrity_assessment.relevant_flags:
            base_conf *= integrity_assessment.confidence_multiplier
            score_multiplier *= integrity_assessment.score_multiplier
            flags.extend(integrity_assessment.flags)
            rationale_parts.append(integrity_assessment.rationale)
            escalate = escalate or integrity_assessment.escalate
        elif integrity_flags:
            base_conf *= 0.95
            flags.append({"type": "integrity_background", "count": len(integrity_flags)})
            rationale_parts.append("Integrity flags were present for the submission but not strongly tied to this criterion.")

        return ArbitrationResult(
            confidence=round(max(0.0, min(1.0, base_conf)), 3),
            rationale=" ".join(rationale_parts),
            flags=flags,
            escalate=escalate,
            blocked=blocked,
            score_multiplier=max(0.0, score_multiplier),
            contradiction_penalty=round(min(1.0, contradiction_penalty), 3),
        )

    def _apply_contradiction_policy(self, criterion: Criterion, report: ContradictionReport) -> tuple[float, float, bool, bool, float, str]:
        severity = report.severity or "none"
        contradictions = max(1, len(report.contradictions))
        severity_penalty = {"low": 0.08, "medium": 0.22, "high": 0.45}.get(severity, 0.0)
        count_penalty = min(0.25, 0.06 * max(0, contradictions - 1))
        subtype_bonus = 0.0
        subtypes = {flag.get("subtype") for flag in report.flags if flag.get("subtype")}
        if {"algorithm_mismatch", "metric_value_mismatch", "metric_threshold_mismatch"} & subtypes:
            subtype_bonus += 0.1
        if "diagram_text_mismatch" in subtypes:
            subtype_bonus += 0.03
        contradiction_penalty = min(0.85, severity_penalty + count_penalty + subtype_bonus)

        policy = getattr(criterion, "contradiction_policy", "discount")
        threshold = getattr(criterion, "contradiction_severity_threshold", "medium")
        sev_rank = self._severity_rank.get(severity, 0)
        thr_rank = self._severity_rank.get(threshold, 2)

        score_multiplier = 1.0
        conf_multiplier = 1.0
        escalate = False
        blocked = False

        if policy == "review_only":
            conf_multiplier *= 0.82 if sev_rank >= 2 else 0.9
            escalate = sev_rank >= thr_rank
            score_multiplier = 1.0
            reason = f"{severity.title()}-severity contradictions were detected; policy kept scoring intact but required review handling."
        elif policy == "block_if_high" and sev_rank >= thr_rank:
            blocked = True
            escalate = True
            score_multiplier = 0.0
            conf_multiplier *= 0.6
            reason = f"{severity.title()}-severity contradictions exceeded the blocking threshold, so this criterion was blocked for manual review."
        else:
            score_multiplier = max(0.0, 1.0 - contradiction_penalty)
            conf_multiplier *= max(0.45, 1.0 - contradiction_penalty * 0.8)
            escalate = sev_rank >= thr_rank
            reason = (
                f"{severity.title()}-severity contradictions triggered a deterministic penalty of {contradiction_penalty:.2f} "
                f"based on severity, count, and contradiction subtype evidence."
            )

        return score_multiplier, conf_multiplier, escalate, blocked, contradiction_penalty, reason
