from __future__ import annotations

from typing import Sequence

from autograde.evaluators import EvaluatorRegistry
from autograde.execution import CodeExecutionProbeEngine
from autograde.executor.claim_graph import ClaimGraphBuilder
from autograde.executor.explanation import build_score_explanation
from autograde.executor.failure_detection import detect_submission_failures
from autograde.executor.criterion_decision import CriterionDecisionEngine
from autograde.executor.adaptive_weighting import AdaptiveWeightingEngine
from autograde.executor.evidence_query import EvidenceQueryEngine
from autograde.executor.review import ReviewBundleBuilder
from autograde.integrity import ExternalSource, IntegrityEngine
from autograde.models import GradingResult, Submission
from autograde.rubric import Rubric, RubricCompiler, RubricValidator


class GradingExecutor:
    def __init__(self) -> None:
        self.compiler = RubricCompiler()
        self.claim_graph_builder = ClaimGraphBuilder()
        self.execution_probe = CodeExecutionProbeEngine()
        self.registry = EvaluatorRegistry()
        self.integrity = IntegrityEngine()
        self.decision_engine = CriterionDecisionEngine()
        self.query_engine = EvidenceQueryEngine()
        self.review_builder = ReviewBundleBuilder()
        self.validator = RubricValidator()
        self.adaptive_weighting = AdaptiveWeightingEngine()

    def grade_submission(
        self,
        submission: Submission,
        rubric: Rubric,
        source_corpus: Sequence[ExternalSource] | None = None,
    ) -> GradingResult:
        validation = self.validator.validate(rubric)
        if not validation.is_valid:
            raise ValueError(f"Invalid rubric: {validation.errors}")
        graph = self.compiler.compile(rubric)
        self.execution_probe.attach_execution_evidence(submission)
        review_flags = self.integrity.check_external_sources(submission, source_corpus=source_corpus)
        global_failures = detect_submission_failures(submission)
        claim_graph = self.claim_graph_builder.build(submission.submission_id, submission.evidence)
        submission.submission_metadata["claim_graph_summary"] = claim_graph.summary()
        criterion_results = []
        review_bundles = []
        explanations = []
        completed: dict[str, object] = {}
        for node in graph.nodes:
            evidence_bundle = self.query_engine.query(submission, node.query_plan)
            evaluator_results = []
            for evaluator_id in node.evaluators:
                evaluator = self.registry.get(evaluator_id)
                if evaluator is None:
                    continue
                evaluator_results.append(evaluator.evaluate(node.criterion, list(evidence_bundle.evidence)))

            dependency_blocked = any(
                getattr(completed.get(dep), "score", 0.0) <= 0.0 or getattr(completed.get(dep), "status", "") in {"blocked", "insufficient_evidence"}
                for dep in node.dependencies
            )
            decision = self.decision_engine.decide(
                criterion=node.criterion,
                evidence_bundle=evidence_bundle,
                evaluator_results=evaluator_results,
                integrity_flags=review_flags,
                low_confidence_threshold=rubric.low_confidence_threshold,
                dependency_blocked=dependency_blocked,
                dependency_results=completed,
                claim_graph=claim_graph,
            )
            criterion_results.append(decision.result)
            explanations.append(build_score_explanation(decision.result))
            completed[node.criterion.criterion_id] = decision.result
            rb = self.review_builder.build_for_criterion(decision.result)
            if rb is not None:
                review_bundles.append({
                    'criterion_id': rb.criterion_id,
                    'reason': rb.reason,
                    'evidence_ids': rb.evidence_ids,
                    'flags': rb.flags,
                    'suggested_action': rb.suggested_action,
                    'priority': rb.priority,
                    'priority_score': rb.priority_score,
                })

        if global_failures:
            review_bundles.append({
                "criterion_id": "__global__",
                "reason": "Submission-level failures detected before or during grading.",
                "evidence_ids": [],
                "flags": global_failures,
                "suggested_action": "manual_review",
                "priority": "critical" if any(f.get("severity") == "critical" for f in global_failures) else "high",
                "priority_score": 100 if any(f.get("severity") == "critical" for f in global_failures) else 85,
            })
        review_bundles.sort(key=lambda x: x.get('priority_score', 0), reverse=True)
        final_score = self._aggregate_scores(criterion_results, rubric, self.adaptive_weighting)
        submission.processing_status["grading"] = "complete"
        submission.manifest.integrity_flags = review_flags
        return GradingResult(
            submission_id=submission.submission_id,
            criterion_results=criterion_results,
            final_score=round(final_score, 2),
            max_score=rubric.normalize_to,
            review_flags=review_flags,
            claim_graph_summary=claim_graph.summary(),
            review_bundles=review_bundles,
            rubric_warnings=validation.warnings,
            explanations=explanations,
            global_failures=global_failures,
        )

    def grade_cohort_similarity(self, submissions: list[Submission]) -> list[dict[str, str]]:
        return self.integrity.check_intra_cohort_similarity(submissions)

    @staticmethod
    def _aggregate_scores(criterion_results, rubric: Rubric, adaptive_weighting: AdaptiveWeightingEngine) -> float:
        weight_map = {c.criterion_id: float(c.weight) for c in rubric.criteria}
        if rubric.adaptive_weighting_enabled:
            decisions = adaptive_weighting.apply(criterion_results, rubric)
            for d in decisions:
                weight_map[d.criterion_id] = d.adjusted_weight
            for result in criterion_results:
                for d in decisions:
                    if d.criterion_id == result.criterion_id:
                        result.evidence_strength = round(d.evidence_strength, 4)
                        result.effective_weight = round(d.adjusted_weight, 6)
                        result.confidence_rationale = (result.confidence_rationale + ' ' + d.rationale).strip()
                        break
        else:
            for result in criterion_results:
                result.effective_weight = round(weight_map.get(result.criterion_id, 0.0), 6)
                result.evidence_strength = 1.0

        final_raw = sum(
            r.score * weight_map.get(r.criterion_id, 0.0)
            for r in criterion_results
        )
        max_weighted = sum(c.max_score * weight_map.get(c.criterion_id, c.weight) for c in rubric.criteria)
        return (final_raw / max_weighted) * rubric.normalize_to if max_weighted else 0.0
