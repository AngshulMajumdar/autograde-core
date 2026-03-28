from __future__ import annotations

__all__ = ["EvaluatorRegistry", "DeterministicEvaluator", "HybridEvaluator", "LLMEvaluator"]


def __getattr__(name: str):
    if name == "EvaluatorRegistry":
        from .registry import EvaluatorRegistry
        return EvaluatorRegistry
    if name in {"DeterministicEvaluator", "HybridEvaluator", "LLMEvaluator"}:
        from .types import DeterministicEvaluator, HybridEvaluator, LLMEvaluator
        return {
            "DeterministicEvaluator": DeterministicEvaluator,
            "HybridEvaluator": HybridEvaluator,
            "LLMEvaluator": LLMEvaluator,
        }[name]
    raise AttributeError(name)
