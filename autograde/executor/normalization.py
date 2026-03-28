from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


_ALGO_ALIASES = {
    "dijkstra": "dijkstra",
    "dijkstra's": "dijkstra",
    "dijkstras": "dijkstra",
    "bfs": "bfs",
    "breadth first search": "bfs",
    "breadth-first search": "bfs",
    "dfs": "dfs",
    "depth first search": "dfs",
    "depth-first search": "dfs",
    "bellman ford": "bellman_ford",
    "bellman-ford": "bellman_ford",
    "floyd warshall": "floyd_warshall",
    "floyd-warshall": "floyd_warshall",
    "a*": "astar",
    "a star": "astar",
    "astar": "astar",
    "a-star": "astar",
    "kruskal": "kruskal",
    "prim": "prim",
}

_DATA_STRUCTURE_ALIASES = {
    "priority queue": "priority_queue",
    "priority_queue": "priority_queue",
    "heap": "priority_queue",
    "heapq": "priority_queue",
    "min heap": "priority_queue",
    "min-heap": "priority_queue",
    "queue": "queue",
    "deque": "queue",
}

_METRIC_ALIASES = {
    "accuracy": "accuracy",
    "acc": "accuracy",
    "precision": "precision",
    "recall": "recall",
    "f1": "f1",
    "f1-score": "f1",
    "f1 score": "f1",
    "error": "error",
    "loss": "loss",
}

_COMPLEXITY_ALIASES = {
    "nlogn": "o(n log n)",
    "n log n": "o(n log n)",
    "n^2": "o(n^2)",
    "n2": "o(n^2)",
}


@dataclass(slots=True)
class NormalizedClaimValue:
    value: str | float
    display_value: str | float
    canonical_subject: str | None = None


class ClaimNormalizer:
    def normalize_algorithm(self, value: str) -> NormalizedClaimValue:
        raw = self._clean_text(value)
        raw = raw.replace(" algorithm", "").strip()
        canonical = _ALGO_ALIASES.get(raw, raw.replace(" ", "_").replace("-", "_"))
        return NormalizedClaimValue(value=canonical, display_value=value, canonical_subject="algorithm")

    def normalize_metric_name(self, metric: str) -> str:
        raw = self._clean_text(metric)
        return _METRIC_ALIASES.get(raw, raw)

    def normalize_metric_subject(self, subject: str) -> str:
        if ":" not in subject:
            return self.normalize_metric_name(subject)
        metric, suffix = subject.split(":", 1)
        return f"{self.normalize_metric_name(metric)}:{suffix}"

    def normalize_numeric_value(self, value: str | float | int, raw_text: str = "") -> NormalizedClaimValue:
        if isinstance(value, (int, float)):
            val = float(value)
        else:
            text = str(value).strip()
            percent = text.endswith("%") or "%" in raw_text
            text = text.rstrip("% ")
            val = float(text)
            if percent and val > 1.0:
                val /= 100.0
            elif not percent and val > 1.0 and val <= 100.0 and any(k in raw_text.lower() for k in ["accuracy", "precision", "recall", "f1", "percent", "%"]):
                # Heuristic: metric claims written as 98 instead of 0.98.
                val /= 100.0
        return NormalizedClaimValue(value=round(val, 6), display_value=value)

    def normalize_complexity(self, value: str) -> NormalizedClaimValue:
        text = self._clean_text(value)
        inner = text.removeprefix("o(").removesuffix(")").strip()
        inner = inner.replace("*", " ").replace("  ", " ")
        inner = re.sub(r"\s+", " ", inner)
        canonical = _COMPLEXITY_ALIASES.get(inner, f"o({inner})")
        return NormalizedClaimValue(value=canonical, display_value=value, canonical_subject="complexity")

    def normalize_data_structure(self, value: str) -> NormalizedClaimValue:
        raw = self._clean_text(value)
        canonical = _DATA_STRUCTURE_ALIASES.get(raw, raw.replace(" ", "_"))
        return NormalizedClaimValue(value=canonical, display_value=value, canonical_subject="data_structure")

    def normalize_feedback_state(self, value: str) -> NormalizedClaimValue:
        raw = self._clean_text(value)
        if raw in {"present", "closed loop", "closed-loop", "feedback loop", "feedback"}:
            canonical = "present"
        elif raw in {"absent", "open loop", "open-loop", "no feedback"}:
            canonical = "absent"
        else:
            canonical = raw.replace(" ", "_")
        return NormalizedClaimValue(value=canonical, display_value=value, canonical_subject="feedback_loop")

    def normalize_claim(self, claim_type: str, subject: str, value: str | float, raw_text: str = "") -> tuple[str, str | float]:
        if subject == "algorithm":
            norm = self.normalize_algorithm(str(value))
            return norm.canonical_subject or subject, norm.value
        if subject == "complexity":
            norm = self.normalize_complexity(str(value))
            return norm.canonical_subject or subject, norm.value
        if subject == "data_structure":
            norm = self.normalize_data_structure(str(value))
            return norm.canonical_subject or subject, norm.value
        if subject == "feedback_loop":
            norm = self.normalize_feedback_state(str(value))
            return norm.canonical_subject or subject, norm.value
        if claim_type.startswith("metric"):
            canonical_subject = self.normalize_metric_subject(subject)
            norm = self.normalize_numeric_value(value, raw_text=raw_text)
            return canonical_subject, norm.value
        return subject, value

    @staticmethod
    def _clean_text(text: str) -> str:
        lowered = text.lower().strip()
        lowered = re.sub(r"[^a-z0-9*%\-\s\^\.]+", " ", lowered)
        lowered = re.sub(r"\s+", " ", lowered)
        return lowered.strip()
