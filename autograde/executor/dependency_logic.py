from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from autograde.models import CriterionResult
from autograde.rubric import Criterion


@dataclass(slots=True)
class DependencyDecision:
    blocked: bool
    cap_fraction: float
    rationale: str


class DependencyLogicEngine:
    def assess(self, criterion: Criterion, completed: Mapping[str, CriterionResult]) -> DependencyDecision:
        if not criterion.depends_on:
            return DependencyDecision(False, 1.0, 'No dependency constraints applied.')
        fail_statuses = {'blocked', 'insufficient_evidence', 'unsupported_needs_review'}
        min_fraction = float(criterion.metadata.get('dependency_min_fraction', 0.5)) if criterion.metadata else 0.5
        weak_cap = float(criterion.metadata.get('dependency_cap_fraction', 0.6)) if criterion.metadata else 0.6
        rationales = []
        cap_fraction = 1.0
        for dep_id in criterion.depends_on:
            dep = completed.get(dep_id)
            if dep is None:
                return DependencyDecision(True, 0.0, f'Dependency {dep_id} was not available, so this criterion was blocked.')
            if dep.status in fail_statuses:
                return DependencyDecision(True, 0.0, f'Dependency {dep_id} had status {dep.status}, so this criterion was blocked.')
            fraction = dep.score / dep.max_score if dep.max_score else 0.0
            rationales.append(f'{dep_id}={fraction:.2f}')
            if fraction < min_fraction:
                cap_fraction = min(cap_fraction, weak_cap)
        rationale = 'Dependency assessment used prerequisite performance: ' + ', '.join(rationales) + '.'
        if cap_fraction < 1.0:
            rationale += f' Downstream score was capped to {cap_fraction:.2f} because prerequisite quality was weak.'
        return DependencyDecision(False, cap_fraction, rationale)
