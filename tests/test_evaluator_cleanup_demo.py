from autograde.evaluators import EvaluatorRegistry


def test_registry_exposes_only_three_evaluator_types():
    registry = EvaluatorRegistry()
    types = set(registry.describe().values())
    assert types == {"deterministic", "llm", "hybrid"}
    assert registry.get("thesis_strength").evaluator_type == "hybrid"
    assert registry.get("llm_argument_quality").evaluator_type == "llm"
    assert registry.get("behavioral_correctness").evaluator_type == "deterministic"
