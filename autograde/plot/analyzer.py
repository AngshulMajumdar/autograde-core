from __future__ import annotations

import cv2
import numpy as np

from autograde.plot.axis_detector import detect_axes, detect_axis_labels
from autograde.plot.curve_detector import detect_curves


class PlotAnalyzer:
    def analyze(self, image):
        if hasattr(image, "convert"):
            arr = np.array(image.convert("RGB"))
            bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        else:
            bgr = image
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        axes = detect_axes(gray)
        labels = detect_axis_labels(gray)
        curves = detect_curves(gray)
        metric_tokens = [
            tok for tok in [
                "accuracy", "acc", "loss", "gain", "cutoff", "bandwidth", "frequency", "time",
                "voltage", "current", "ber", "snr", "precision", "recall", "f1"
            ] if tok in labels
        ]
        return {
            "axes": axes,
            "labels": labels,
            "curves": curves,
            "metric_tokens": metric_tokens,
        }
