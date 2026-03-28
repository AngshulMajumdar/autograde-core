from __future__ import annotations

import re
from typing import Any, Dict

import cv2
import numpy as np

from autograde.diagram.detectors import detect_lines, detect_text
from autograde.diagram.graph_builder import build_graph


class DiagramAnalyzer:
    def analyze(self, image) -> Dict[str, Any]:
        if hasattr(image, "convert"):
            arr = np.array(image.convert("RGB"))
            bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        else:
            bgr = image
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        lines = detect_lines(gray)
        texts = detect_text(gray)
        graph = build_graph(lines, texts)
        return {
            "lines": lines,
            "texts": texts,
            "graph": graph,
        }

    def analyze_svg(self, raw: str) -> Dict[str, Any]:
        labels = re.findall(r">\s*([A-Za-z][A-Za-z0-9_+\-]*)\s*<", raw)
        labels += re.findall(r"id=[\'\"]([^\'\"]+)[\'\"]", raw)
        labels = labels[:30]
        texts = [{"text": t, "x": i * 80 + 20, "y": 20, "w": max(20, len(t) * 7), "h": 12, "confidence": 0.8} for i, t in enumerate(labels)]
        line_count = len(re.findall(r"<(?:line|polyline|path)\b", raw.lower()))
        lines = [(i * 80 + 55, 24, i * 80 + 95, 24) for i in range(max(0, min(line_count, max(0, len(texts) - 1))))]
        graph = build_graph(lines, texts)
        if graph.get("edge_count", 0) < min(line_count, max(0, len(texts) - 1)):
            nodes = graph.get("nodes", [])
            edges = []
            for i in range(min(line_count, max(0, len(nodes) - 1))):
                edges.append({
                    "id": f"svg_e{i}",
                    "source": nodes[i]["id"],
                    "target": nodes[i+1]["id"],
                    "type": graph.get("relation_types", ["generic_relation"])[0] if graph.get("relation_types") else "generic_relation",
                })
            graph["edges"] = edges
            graph["edge_count"] = len(edges)
            graph["relation_types"] = sorted({e["type"] for e in edges})
        return {
            "lines": lines,
            "texts": texts,
            "graph": graph,
        }
