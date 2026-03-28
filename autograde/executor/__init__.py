from __future__ import annotations

__all__ = [
    "GradingExecutor",
    "CriterionDecisionEngine",
    "EvidenceSufficiencyChecker",
    "ScoringPolicyEngine",
    "ArbitrationPolicy",
    "ClaimGraphBuilder",
    "ClaimGraph",
    "IntegrityPolicyRouter",
]


def __getattr__(name: str):
    if name == "GradingExecutor":
        from .engine import GradingExecutor
        return GradingExecutor
    if name == "CriterionDecisionEngine":
        from .criterion_decision import CriterionDecisionEngine
        return CriterionDecisionEngine
    if name == "EvidenceSufficiencyChecker":
        from .evidence_sufficiency import EvidenceSufficiencyChecker
        return EvidenceSufficiencyChecker
    if name == "ScoringPolicyEngine":
        from .scoring_policies import ScoringPolicyEngine
        return ScoringPolicyEngine
    if name == "ArbitrationPolicy":
        from .arbitration import ArbitrationPolicy
        return ArbitrationPolicy
    if name in {"ClaimGraphBuilder", "ClaimGraph"}:
        from .claim_graph import ClaimGraphBuilder, ClaimGraph
        return {"ClaimGraphBuilder": ClaimGraphBuilder, "ClaimGraph": ClaimGraph}[name]
    if name == "IntegrityPolicyRouter":
        from .integrity_policy import IntegrityPolicyRouter
        return IntegrityPolicyRouter
    raise AttributeError(name)
