from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from autograde.models import EvaluatorResult
from autograde.rubric import Criterion


@dataclass(slots=True)
class PartialCreditDecision:
    score: float
    rationale: str
    missing_required: list[str]


class PartialCreditEngine:
    def compute(self, criterion: Criterion, evaluator_results: Sequence[EvaluatorResult]) -> PartialCreditDecision | None:
        if not criterion.subcomponents:
            return None
        result_map = {r.evaluator_id: r for r in evaluator_results}
        total = 0.0
        weight_sum = 0.0
        missing_required: list[str] = []
        parts: list[str] = []
        for sub in criterion.subcomponents:
            weight = max(0.0, float(sub.weight))
            if weight == 0.0:
                continue
            er = result_map.get(sub.evaluator_id)
            frac = 0.0
            if er is None or er.max_score <= 0:
                if sub.required:
                    missing_required.append(sub.name)
                parts.append(f"{sub.name}=missing")
            else:
                frac = max(0.0, min(1.0, er.score / er.max_score))
                if sub.required and frac <= 0.05:
                    missing_required.append(sub.name)
                parts.append(f"{sub.name}={frac:.2f}")
            total += frac * weight
            weight_sum += weight
        if weight_sum <= 0:
            return PartialCreditDecision(0.0, 'Subcomponent partial-credit scoring found no usable weights.', missing_required)
        score = criterion.max_score * (total / weight_sum)
        rationale = 'Partial-credit scoring used criterion subcomponents: ' + ', '.join(parts) + '.'
        if missing_required:
            rationale += ' Required subcomponents missing or effectively absent: ' + ', '.join(missing_required) + '.'
        return PartialCreditDecision(round(score,2), rationale, missing_required)
