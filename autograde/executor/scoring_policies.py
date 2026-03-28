from __future__ import annotations

from statistics import mean
from typing import Sequence

from autograde.models import EvaluatorResult
from autograde.rubric import Criterion
from autograde.executor.partial_credit import PartialCreditEngine


class ScoringPolicyEngine:
    def __init__(self) -> None:
        self.partial_credit = PartialCreditEngine()

    def score(
        self,
        criterion: Criterion,
        evaluator_results: Sequence[EvaluatorResult],
        sufficiency_status: str,
        score_multiplier: float = 1.0,
        dependency_blocked: bool = False,
        dependency_cap_fraction: float = 1.0,
        coverage_status: str = 'covered',
        coverage_score: float = 1.0,
    ) -> tuple[float, str]:
        mode = criterion.scoring_policy.mode or 'analytic_bands'
        if dependency_blocked:
            return 0.0, 'Scoring was blocked because a prerequisite criterion did not pass.'
        if not evaluator_results:
            return 0.0, 'No evaluator results available.'
        pc = self.partial_credit.compute(criterion, evaluator_results)
        if pc is not None:
            score, rationale = pc.score, pc.rationale
            if pc.missing_required:
                score = min(score, criterion.max_score * 0.7)
                rationale += ' Required subcomponents triggered a partial-credit cap.'
        elif mode == 'checklist':
            score, rationale = self._checklist(criterion, evaluator_results)
        elif mode == 'gated_score':
            score, rationale = self._gated_score(criterion, evaluator_results, sufficiency_status)
        elif mode == 'weighted_average':
            score, rationale = self._weighted_average(criterion, evaluator_results)
        else:
            score, rationale = self._analytic_bands(criterion, evaluator_results, sufficiency_status)
        score, coverage_rationale = self._apply_coverage(criterion, score, coverage_status, coverage_score)
        rationale = f"{rationale} {coverage_rationale}".strip()
        if dependency_cap_fraction < 1.0:
            score = min(score, criterion.max_score * dependency_cap_fraction)
            rationale += f' Dependency rules capped the score to {dependency_cap_fraction:.2f} of criterion maximum.'
        score = min(criterion.max_score, max(0.0, score * score_multiplier))
        if score_multiplier != 1.0:
            rationale += f' Final score was multiplied by {score_multiplier:.2f} after arbitration.'
        return round(score, 2), rationale

    @staticmethod
    def _analytic_bands(criterion: Criterion, evaluator_results: Sequence[EvaluatorResult], sufficiency_status: str) -> tuple[float, str]:
        raw = mean(r.score for r in evaluator_results)
        normalized = raw / criterion.max_score if criterion.max_score else 0.0
        if sufficiency_status == 'insufficient':
            normalized = 0.0 if criterion.zero_if_missing else min(normalized, 0.2)
            rationale = 'Analytic-band scoring was capped because evidence was insufficient.'
        elif sufficiency_status == 'ambiguous':
            normalized *= 0.8
            rationale = 'Analytic-band scoring was discounted because evidence was ambiguous.'
        else:
            rationale = 'Analytic-band scoring used the mean of evaluator judgments.'
        return round(normalized * criterion.max_score, 2), rationale

    @staticmethod
    def _weighted_average(criterion: Criterion, evaluator_results: Sequence[EvaluatorResult]) -> tuple[float, str]:
        weights = [max(r.confidence, 0.05) for r in evaluator_results]
        total = sum(weights)
        weighted = sum(r.score * w for r, w in zip(evaluator_results, weights)) / total if total else 0.0
        return round(min(weighted, criterion.max_score), 2), 'Weighted-average scoring used evaluator confidence as weights.'

    @staticmethod
    def _checklist(criterion: Criterion, evaluator_results: Sequence[EvaluatorResult]) -> tuple[float, str]:
        passed = sum(1 for r in evaluator_results if r.score >= 0.6 * r.max_score)
        score = criterion.max_score * (passed / len(evaluator_results))
        return round(score, 2), 'Checklist scoring counted evaluators meeting the pass threshold.'

    @staticmethod
    def _gated_score(criterion: Criterion, evaluator_results: Sequence[EvaluatorResult], sufficiency_status: str) -> tuple[float, str]:
        base = mean(r.score for r in evaluator_results)
        params = criterion.scoring_policy.params or {}
        gate_evaluator = params.get('gate_on')
        gate_threshold = float(params.get('gate_threshold', 0.5))
        cap_fraction = float(params.get('cap_fraction', 0.35))
        rationale = 'Gated scoring used the base mean score.'
        if sufficiency_status != 'sufficient':
            capped = 0.0 if criterion.zero_if_missing else min(base, criterion.max_score * 0.2)
            return round(capped, 2), 'Gated scoring capped the score because evidence was not fully sufficient.'
        if gate_evaluator:
            for result in evaluator_results:
                if result.evaluator_id == gate_evaluator:
                    if result.max_score and (result.score / result.max_score) < gate_threshold:
                        capped = min(base, criterion.max_score * cap_fraction)
                        return round(capped, 2), f'Gated scoring capped the score because {gate_evaluator} did not meet the threshold.'
                    break
        return round(min(base, criterion.max_score), 2), rationale

    @staticmethod
    def _apply_coverage(criterion: Criterion, score: float, coverage_status: str, coverage_score: float) -> tuple[float, str]:
        if coverage_status == 'missing_required':
            cap = criterion.max_score * 0.6
            return min(score, cap), 'Coverage rules capped the score because required aspects were missing.'
        if coverage_status == 'partial':
            factor = max(0.7, coverage_score)
            return score * factor, 'Coverage rules discounted the score because some required aspects were only weakly covered.'
        return score, 'Coverage rules found adequate aspect coverage.'
