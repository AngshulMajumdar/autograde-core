from __future__ import annotations

import cv2
import pytesseract


def detect_axes(gray):
    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, 3.14159 / 180, threshold=80, minLineLength=80, maxLineGap=10)
    axes = []
    if lines is None:
        return axes
    for line in lines:
        x1, y1, x2, y2 = line[0]
        if abs(x1 - x2) < 5:
            axes.append("y")
        if abs(y1 - y2) < 5:
            axes.append("x")
    return sorted(set(axes))


def detect_axis_labels(gray):
    try:
        data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)
    except Exception:
        return []
    labels = []
    for txt in data.get("text", []):
        txt = (txt or "").strip()
        if txt:
            labels.append(txt.lower())
    return labels
