from __future__ import annotations

__all__ = [
    "CriterionAspect",
    "Criterion",
    "CriterionSubcomponent",
    "Rubric",
    "ScoringPolicy",
    "CriterionNode",
    "GradingGraph",
    "RubricCompiler",
    "RubricValidationResult",
    "RubricValidator",
    "PastCase",
    "RubricInducer",
    "induce_rubric_from_past_cases",
    "RubricDriftDetector",
    "RubricDriftReport",
]



def __getattr__(name: str):
    if name == "CriterionAspect":
        from autograde.coverage.aspect_model import CriterionAspect
        return CriterionAspect
    if name in {"Criterion", "Rubric", "ScoringPolicy"}:
        from .schema import Criterion, Rubric, ScoringPolicy
        return {"Criterion": Criterion, "Rubric": Rubric, "ScoringPolicy": ScoringPolicy}[name]
    if name in {"CriterionNode", "GradingGraph", "RubricCompiler"}:
        from .compiler import CriterionNode, GradingGraph, RubricCompiler
        return {"CriterionNode": CriterionNode, "GradingGraph": GradingGraph, "RubricCompiler": RubricCompiler}[name]
    if name in {"RubricValidationResult", "RubricValidator"}:
        from .validator import RubricValidationResult, RubricValidator
        return {"RubricValidationResult": RubricValidationResult, "RubricValidator": RubricValidator}[name]
    raise AttributeError(name)


def __getattr_extra(name: str):
    if name in {"PastCase", "RubricInducer", "induce_rubric_from_past_cases"}:
        from .induction import PastCase, RubricInducer, induce_rubric_from_past_cases
        return {"PastCase": PastCase, "RubricInducer": RubricInducer, "induce_rubric_from_past_cases": induce_rubric_from_past_cases}[name]
    if name in {"RubricDriftDetector", "RubricDriftReport"}:
        from .drift import RubricDriftDetector, RubricDriftReport
        return {"RubricDriftDetector": RubricDriftDetector, "RubricDriftReport": RubricDriftReport}[name]
    raise AttributeError(name)

_old_getattr = __getattr__
def __getattr__(name: str):
    try:
        return _old_getattr(name)
    except AttributeError:
        return __getattr_extra(name)
