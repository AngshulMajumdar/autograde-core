from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from autograde.rubric.schema import Rubric


@dataclass(slots=True)
class RubricValidationResult:
    is_valid: bool
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)


class RubricValidator:
    SUPPORTED_SCORING_MODES = {"analytic_bands", "weighted_average", "checklist", "gated_score"}
    SUPPORTED_INTEGRITY_POLICIES = {"ignore", "review_only", "discount_if_relevant", "block_if_high"}
    SUPPORTED_CONTRADICTION_POLICIES = {"review_only", "discount", "block_if_high"}
    SUPPORTED_INTEGRITY_SCOPES = {"auto", "text", "code", "all"}

    def validate(self, rubric: Rubric) -> RubricValidationResult:
        errors: List[Dict[str, Any]] = []
        warnings: List[Dict[str, Any]] = []
        if not rubric.criteria:
            errors.append({"type": "empty_rubric", "message": "Rubric must contain at least one criterion."})
            return RubricValidationResult(False, errors, warnings)

        criterion_ids = set()
        weight_sum = 0.0
        available_ids = set()
        for c in rubric.criteria:
            available_ids.add(c.criterion_id)

        for c in rubric.criteria:
            if c.criterion_id in criterion_ids:
                errors.append({"type": "duplicate_criterion_id", "criterion_id": c.criterion_id})
            criterion_ids.add(c.criterion_id)
            weight_sum += c.weight

            if c.max_score <= 0:
                errors.append({"type": "invalid_max_score", "criterion_id": c.criterion_id, "value": c.max_score})
            if c.weight < 0:
                errors.append({"type": "negative_weight", "criterion_id": c.criterion_id, "value": c.weight})
            if c.scoring_policy.mode not in self.SUPPORTED_SCORING_MODES:
                errors.append({"type": "unsupported_scoring_mode", "criterion_id": c.criterion_id, "mode": c.scoring_policy.mode})
            if c.integrity_policy not in self.SUPPORTED_INTEGRITY_POLICIES:
                errors.append({"type": "unsupported_integrity_policy", "criterion_id": c.criterion_id, "value": c.integrity_policy})
            if c.integrity_scope not in self.SUPPORTED_INTEGRITY_SCOPES:
                errors.append({"type": "unsupported_integrity_scope", "criterion_id": c.criterion_id, "value": c.integrity_scope})
            if c.zero_if_missing and not c.required_modalities and not c.aspects:
                warnings.append({"type": "zero_if_missing_without_requirements", "criterion_id": c.criterion_id})
            if c.minimum_evidence_count < 0:
                errors.append({"type": "invalid_minimum_evidence_count", "criterion_id": c.criterion_id, "value": c.minimum_evidence_count})
            if c.required_modalities and not c.evaluator_hints:
                warnings.append({"type": "no_evaluators", "criterion_id": c.criterion_id})
            if c.cross_check_policy not in {"advisory", "binding"}:
                errors.append({"type": "invalid_cross_check_policy", "criterion_id": c.criterion_id, "value": c.cross_check_policy})
            if c.contradiction_policy not in self.SUPPORTED_CONTRADICTION_POLICIES:
                errors.append({"type": "invalid_contradiction_policy", "criterion_id": c.criterion_id, "value": c.contradiction_policy})
            if c.contradiction_severity_threshold not in {"low", "medium", "high"}:
                errors.append({"type": "invalid_contradiction_severity_threshold", "criterion_id": c.criterion_id, "value": c.contradiction_severity_threshold})
            for dep in c.depends_on:
                if dep not in available_ids:
                    errors.append({"type": "unknown_dependency", "criterion_id": c.criterion_id, "depends_on": dep})
            if c.scoring_policy.mode == 'gated_score':
                params = c.scoring_policy.params or {}
                if 'gate_evaluator' not in params:
                    errors.append({"type": "missing_gate_evaluator", "criterion_id": c.criterion_id})
                if not 0 <= float(params.get('cap_fraction', 1.0)) <= 1:
                    errors.append({"type": "invalid_cap_fraction", "criterion_id": c.criterion_id, "value": params.get('cap_fraction')})

        if weight_sum <= 0:
            errors.append({"type": "nonpositive_weight_sum", "value": weight_sum})
        elif abs(weight_sum - 1.0) > 0.05:
            warnings.append({"type": "weight_sum_not_one", "value": round(weight_sum, 4)})

        return RubricValidationResult(not errors, errors, warnings)
