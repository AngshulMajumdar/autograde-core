from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Sequence

from autograde.models import EvidenceObject, EvaluatorResult

if TYPE_CHECKING:
    from autograde.rubric.schema import Criterion


class BaseEvaluator(ABC):
    evaluator_id = "base"
    evaluator_type = "base"

    @abstractmethod
    def evaluate(self, criterion: "Criterion", evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        raise NotImplementedError
