from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List

from autograde.rubric.induction import PastCase, RubricInducer
from autograde.rubric.schema import Rubric


@dataclass(slots=True)
class CriterionDrift:
    old_name: str
    status: str
    new_name: str | None = None
    old_weight: float | None = None
    new_weight: float | None = None
    delta_weight: float | None = None


@dataclass(slots=True)
class RubricDriftReport:
    subject_profile: str
    old_criteria_count: int
    new_criteria_count: int
    changed: List[CriterionDrift] = field(default_factory=list)
    added: List[str] = field(default_factory=list)
    removed: List[str] = field(default_factory=list)
    significant_drift: bool = False


class RubricDriftDetector:
    def __init__(self) -> None:
        self.inducer = RubricInducer()

    def induce_and_compare(self, baseline: Rubric, recent_cases: Iterable[PastCase], subject_profile: str) -> RubricDriftReport:
        induced = self.inducer.induce(list(recent_cases), subject_profile)
        return self.compare(baseline, induced, subject_profile)

    def compare(self, baseline: Rubric, induced: Rubric, subject_profile: str) -> RubricDriftReport:
        old = {c.name.strip().lower().replace(' ', '_'): c for c in baseline.criteria}
        new = {c.name.strip().lower().replace(' ', '_'): c for c in induced.criteria}
        changed: List[CriterionDrift] = []
        added = sorted([name for name in new.keys() if name not in old])
        removed = sorted([name for name in old.keys() if name not in new])
        significant = False
        for name, old_criterion in old.items():
            if name not in new:
                changed.append(CriterionDrift(old_name=name, status='removed', old_weight=old_criterion.weight))
                significant = True
                continue
            new_criterion = new[name]
            delta = float(new_criterion.weight) - float(old_criterion.weight)
            status = 'unchanged'
            if abs(delta) >= 0.15:
                status = 'major_weight_shift'
                significant = True
            elif abs(delta) >= 0.07:
                status = 'minor_weight_shift'
            changed.append(CriterionDrift(
                old_name=name,
                status=status,
                new_name=name,
                old_weight=float(old_criterion.weight),
                new_weight=float(new_criterion.weight),
                delta_weight=round(delta, 4),
            ))
        if added:
            significant = True
        return RubricDriftReport(
            subject_profile=subject_profile,
            old_criteria_count=len(old),
            new_criteria_count=len(new),
            changed=changed,
            added=added,
            removed=removed,
            significant_drift=significant,
        )
