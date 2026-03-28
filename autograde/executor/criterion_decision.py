from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Sequence

from autograde.coverage import CoverageChecker
from autograde.executor.arbitration import ArbitrationPolicy
from autograde.executor.claim_graph import ClaimGraph
from autograde.executor.confidence import ConfidenceCalibrator
from autograde.executor.claim_evidence import ClaimEvidenceReasoner
from autograde.executor.capability import CapabilityGatingEngine
from autograde.executor.contradiction_detector import ContradictionDetector
from autograde.executor.cross_checks import CrossCheckEngine
from autograde.executor.dependency_logic import DependencyLogicEngine
from autograde.executor.evidence_query import EvidenceBundle
from autograde.executor.evidence_sufficiency import EvidenceSufficiencyChecker
from autograde.executor.integrity_policy import IntegrityPolicyRouter
from autograde.executor.scoring_policies import ScoringPolicyEngine
from autograde.models import CriterionResult, EvaluatorResult
from autograde.rubric import Criterion


@dataclass(slots=True)
class CriterionDecision:
    result: CriterionResult
    status: str
    flags: list[Dict[str, Any]] = field(default_factory=list)


class CriterionDecisionEngine:
    def __init__(self) -> None:
        self.capability = CapabilityGatingEngine()
        self.sufficiency = EvidenceSufficiencyChecker()
        self.coverage = CoverageChecker()
        self.scoring = ScoringPolicyEngine()
        self.arbitration = ArbitrationPolicy()
        self.cross_checks = CrossCheckEngine()
        self.dependency_logic = DependencyLogicEngine()
        self.contradictions = ContradictionDetector()
        self.claim_evidence = ClaimEvidenceReasoner()
        self.integrity = IntegrityPolicyRouter()
        self.confidence = ConfidenceCalibrator()

    def decide(
        self,
        criterion: Criterion,
        evidence_bundle: EvidenceBundle,
        evaluator_results: Sequence[EvaluatorResult],
        integrity_flags: Sequence[Dict[str, Any]] | None = None,
        low_confidence_threshold: float = 0.65,
        dependency_blocked: bool = False,
        dependency_results: dict[str, CriterionResult] | None = None,
        claim_graph: ClaimGraph | None = None,
    ) -> CriterionDecision:
        dependency_decision = self.dependency_logic.assess(criterion, dependency_results or {})
        capability = self.capability.assess(criterion, evidence_bundle)
        sufficiency = self.sufficiency.assess(criterion, evidence_bundle)
        coverage = self.coverage.assess(criterion, evidence_bundle)
        contradiction_report = self.contradictions.detect(criterion, evidence_bundle, claim_graph=claim_graph)
        claim_evidence_assessment = self.claim_evidence.assess(criterion, evidence_bundle, claim_graph=claim_graph)
        cross_check_results = self.cross_checks.run(criterion.cross_checks, list(evidence_bundle.evidence))
        integrity_assessment = self.integrity.assess(criterion, evidence_bundle, integrity_flags=integrity_flags)
        arbitration = self.arbitration.resolve(
            criterion=criterion,
            evaluator_results=evaluator_results,
            criterion_max_score=criterion.max_score,
            integrity_flags=integrity_flags,
            cross_check_results=cross_check_results,
            contradiction_report=contradiction_report,
            integrity_assessment=integrity_assessment,
            claim_evidence_assessment=claim_evidence_assessment,
        )
        effective_sufficiency = sufficiency.status
        if capability.capability_status == 'unsupported':
            effective_sufficiency = 'insufficient'
        score, scoring_rationale = self.scoring.score(
            criterion,
            evaluator_results,
            effective_sufficiency,
            score_multiplier=arbitration.score_multiplier * (0.6 if capability.support_status == 'partial' else 1.0),
            dependency_blocked=dependency_blocked or dependency_decision.blocked,
            dependency_cap_fraction=dependency_decision.cap_fraction,
            coverage_status=coverage.overall_status,
            coverage_score=coverage.coverage_score,
        )

        llm_results = [r for r in evaluator_results if r.evaluator_id.startswith('llm_')]
        if llm_results:
            llm_weight = float(criterion.metadata.get('llm_weight', 0.25)) if criterion.metadata else 0.25
            llm_weight = max(0.0, min(0.5, llm_weight))
            llm_score = sum(r.score for r in llm_results) / max(1, len(llm_results))
            score = (1.0 - llm_weight) * score + llm_weight * llm_score
            scoring_rationale += f' LLM evaluator outputs were blended with bounded weight {llm_weight:.2f}; deterministic scoring remained dominant.'

        evidence_ids = sorted({eid for r in evaluator_results for eid in r.supporting_evidence})
        evidence_ids = sorted(
            set(evidence_ids)
            | set(evidence_bundle.direct_ids)
            | set(evidence_bundle.supporting_ids)
            | {eid for c in contradiction_report.contradictions for eid in c.evidence_ids}
            | {eid for a in coverage.aspect_results for eid in a.evidence_ids}
        )
        eval_flags = [flag for r in evaluator_results for flag in r.flags]
        cross_flags = [flag for c in cross_check_results for flag in c.flags]
        contradiction_flags = list(contradiction_report.flags)
        claim_flags = list(claim_evidence_assessment.flags)
        all_flags = list(capability.flags) + list(sufficiency.flags) + list(coverage.flags) + list(arbitration.flags) + cross_flags + contradiction_flags + claim_flags + eval_flags + list(integrity_assessment.relevant_flags)

        status = 'graded'
        if dependency_blocked or dependency_decision.blocked or arbitration.blocked:
            status = 'blocked'
        elif capability.capability_status == 'unsupported':
            status = 'unsupported_needs_review'
        elif sufficiency.status == 'insufficient':
            status = 'insufficient_evidence'
        elif arbitration.escalate or sufficiency.status == 'ambiguous':
            status = 'escalated'
        elif capability.support_status == 'partial' and score > 0:
            status = 'partially_graded'
        elif coverage.overall_status == 'missing_required' and criterion.zero_if_missing:
            status = 'insufficient_evidence'

        calibrated = self.confidence.calibrate(
            evaluator_results=evaluator_results,
            sufficiency=sufficiency,
            capability=capability,
            coverage=coverage,
            contradiction_report=contradiction_report,
            arbitration=arbitration,
        )

        manual_review_required = (
            status != 'graded'
            or calibrated.confidence < low_confidence_threshold
            or capability.support_status != 'supported'
            or contradiction_report.severity in {'high', 'medium'}
            or claim_evidence_assessment.overall_status in {'contradicted'}
            or any(flag.get('type') in {'parse_error', 'integrity_interaction', 'cross_check_failure', 'contradiction', 'unsupported_modality', 'missing_required_modality'} for flag in all_flags)
        )

        rationale_parts = [
            capability.rationale,
            sufficiency.rationale,
            coverage.rationale,
            contradiction_report.rationale,
            claim_evidence_assessment.rationale,
            integrity_assessment.rationale,
            *(c.rationale for c in cross_check_results),
            dependency_decision.rationale,
            arbitration.rationale,
            scoring_rationale,
            calibrated.rationale,
            ' '.join(r.rationale for r in evaluator_results if r.rationale),
        ]
        rationale = ' '.join(part.strip() for part in rationale_parts if part and part.strip())

        criterion_result = CriterionResult(
            criterion_id=criterion.criterion_id,
            score=round(score, 2),
            max_score=criterion.max_score,
            confidence=calibrated.confidence,
            rationale=rationale,
            evaluator_results=list(evaluator_results),
            manual_review_required=manual_review_required,
            evidence_ids=evidence_ids,
            status=status,
            flags=all_flags,
            cross_check_results=[
                {
                    'check_id': c.check_id,
                    'passed': c.passed,
                    'confidence': c.confidence,
                    'rationale': c.rationale,
                }
                for c in cross_check_results
            ],
            contradiction_results=[
                {
                    'type': c.contradiction_type,
                    'passed': c.passed,
                    'confidence': c.confidence,
                    'rationale': c.rationale,
                    'evidence_ids': c.evidence_ids,
                }
                for c in contradiction_report.contradictions
            ],
            claim_evidence_results=[
                {
                    'claim_id': link.claim_id,
                    'subject': link.subject,
                    'claim_type': link.claim_type,
                    'claim_value': link.claim_value,
                    'support_status': link.support_status,
                    'confidence': link.confidence,
                    'rationale': link.rationale,
                    'supporting_claim_ids': link.supporting_claim_ids,
                    'contradicting_claim_ids': link.contradicting_claim_ids,
                    'evidence_ids': link.evidence_ids,
                }
                for link in claim_evidence_assessment.links
            ],
            coverage_results=[
                {
                    'aspect_id': a.aspect_id,
                    'status': a.status,
                    'confidence': a.confidence,
                    'rationale': a.rationale,
                    'evidence_ids': a.evidence_ids,
                }
                for a in coverage.aspect_results
            ],
            coverage_status=coverage.overall_status,
            capability_status=capability.capability_status,
            support_status=capability.support_status,
            confidence_factors=calibrated.factors,
            confidence_rationale=calibrated.rationale,
            contradiction_penalty=arbitration.contradiction_penalty,
        )
        return CriterionDecision(result=criterion_result, status=status, flags=all_flags)
