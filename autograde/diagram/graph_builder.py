from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple
import math


def _center(item: Dict[str, Any]) -> Tuple[float, float]:
    return (item.get("x", 0) + item.get("w", 0) / 2.0, item.get("y", 0) + item.get("h", 0) / 2.0)


def _point_to_segment_distance(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> float:
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)
    t = ((px - x1) * dx + (py - y1) * dy) / float(dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    proj_x, proj_y = x1 + t * dx, y1 + t * dy
    return math.hypot(px - proj_x, py - proj_y)


def _family_from_labels(labels: Iterable[str]) -> str:
    joined = " ".join(labels).lower()
    if any(tok in joined for tok in ["clk", "clock", "posedge", "negedge", "setup", "hold", "delay", "reset", "enable"]):
        return "timing_diagram"
    if any(tok in joined for tok in ["class", "interface", "controller", "service", "repository", "entity", "module"]):
        return "uml_or_architecture"
    if any(tok in joined for tok in ["input", "output", "sum", "plant", "controller", "feedback", "gain"]):
        return "block_diagram"
    return "generic_diagram"


def _infer_edge_type(src: str, dst: str, family: str) -> str:
    low = f"{src} {dst}".lower()
    if family == "timing_diagram":
        return "signal_timing_relation"
    if family == "uml_or_architecture":
        if any(tok in low for tok in ["service", "controller", "repository", "module", "class", "interface"]):
            return "component_relation"
        return "design_relation"
    if family == "block_diagram":
        if any(tok in low for tok in ["input", "output", "controller", "plant", "feedback"]):
            return "flow_relation"
        return "block_relation"
    return "generic_relation"


def build_graph(lines: List[Tuple[int, int, int, int]], texts: List[Dict[str, Any]]) -> Dict[str, Any]:
    labels = [t["text"] for t in texts]
    family = _family_from_labels(labels)
    nodes = []
    for i, t in enumerate(texts):
        nodes.append({
            "id": f"n{i+1}",
            "label": t["text"],
            "pos": _center(t),
            "confidence": t.get("confidence", 0.0),
        })

    edges: List[Dict[str, Any]] = []
    # Link labels that lie close to the same line segment.
    for li, (x1, y1, x2, y2) in enumerate(lines):
        touched: List[int] = []
        for idx, t in enumerate(texts):
            cx, cy = _center(t)
            d = _point_to_segment_distance(cx, cy, x1, y1, x2, y2)
            if d <= 28:
                touched.append(idx)
        # Connect nearby labels in appearance order on this line.
        if len(touched) >= 2:
            touched = sorted(set(touched), key=lambda i: (_center(texts[i])[0], _center(texts[i])[1]))
            for a, b in zip(touched, touched[1:]):
                src = nodes[a]["id"]
                dst = nodes[b]["id"]
                edges.append({
                    "id": f"e{li}_{a}_{b}",
                    "source": src,
                    "target": dst,
                    "type": _infer_edge_type(nodes[a]["label"], nodes[b]["label"], family),
                })

    # Fallback relation chain if labels exist but geometry is sparse.
    if not edges and len(nodes) >= 2:
        for i in range(len(nodes) - 1):
            edges.append({
                "id": f"ef{i}",
                "source": nodes[i]["id"],
                "target": nodes[i+1]["id"],
                "type": _infer_edge_type(nodes[i]["label"], nodes[i+1]["label"], family),
            })

    relation_types = sorted({e["type"] for e in edges})
    return {
        "family": family,
        "nodes": nodes,
        "edges": edges,
        "relation_types": relation_types,
        "node_count": len(nodes),
        "edge_count": len(edges),
    }
