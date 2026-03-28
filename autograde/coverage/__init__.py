from __future__ import annotations

__all__ = [
    "CriterionAspect",
    "AspectCoverageResult",
    "CoverageAssessment",
    "CoverageChecker",
]


def __getattr__(name: str):
    if name in {"CriterionAspect", "AspectCoverageResult", "CoverageAssessment"}:
        from .aspect_model import CriterionAspect, AspectCoverageResult, CoverageAssessment
        return {
            "CriterionAspect": CriterionAspect,
            "AspectCoverageResult": AspectCoverageResult,
            "CoverageAssessment": CoverageAssessment,
        }[name]
    if name == "CoverageChecker":
        from .coverage_checker import CoverageChecker
        return CoverageChecker
    raise AttributeError(name)
