from __future__ import annotations

import cv2


def detect_curves(gray):
    edges = cv2.Canny(gray, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    curves = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > 200:
            curves.append({"points": len(contour), "area": float(area)})
    return curves
