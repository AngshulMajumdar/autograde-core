from __future__ import annotations

from typing import Any, Dict, List

import cv2
import pytesseract


def detect_lines(gray) -> List[tuple[int, int, int, int]]:
    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, 3.14159 / 180, threshold=50, minLineLength=35, maxLineGap=8)
    out: List[tuple[int, int, int, int]] = []
    if lines is None:
        return out
    for line in lines:
        x1, y1, x2, y2 = [int(v) for v in line[0]]
        out.append((x1, y1, x2, y2))
    return out


def detect_text(gray) -> List[Dict[str, Any]]:
    try:
        data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)
    except Exception:
        return []
    out: List[Dict[str, Any]] = []
    n = len(data.get("text", []))
    for i in range(n):
        txt = (data["text"][i] or "").strip()
        if not txt:
            continue
        conf_raw = str(data.get("conf", ["-1"] * n)[i])
        try:
            conf = max(0.0, min(1.0, float(conf_raw) / 100.0))
        except Exception:
            conf = 0.0
        out.append({
            "text": txt,
            "x": int(data["left"][i]),
            "y": int(data["top"][i]),
            "w": int(data["width"][i]),
            "h": int(data["height"][i]),
            "confidence": conf,
        })
    return out
