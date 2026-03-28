from __future__ import annotations

from enum import IntEnum
from typing import Dict


class CapabilityLevel(IntEnum):
    NONE = 0
    WEAK = 1
    PARTIAL = 2
    STRONG = 3


CAPABILITY_REGISTRY: Dict[str, CapabilityLevel] = {
    "text": CapabilityLevel.STRONG,
    "text_reasoning": CapabilityLevel.STRONG,
    "citation": CapabilityLevel.PARTIAL,
    "code": CapabilityLevel.STRONG,
    "code_execution": CapabilityLevel.STRONG,
    "execution": CapabilityLevel.STRONG,
    "diagram": CapabilityLevel.PARTIAL,
    "diagram_topology": CapabilityLevel.PARTIAL,
    "image": CapabilityLevel.PARTIAL,
    "image_ocr": CapabilityLevel.PARTIAL,
    "plot_analysis": CapabilityLevel.PARTIAL,
    "table": CapabilityLevel.PARTIAL,
    "equation": CapabilityLevel.PARTIAL,
    "math_proof": CapabilityLevel.PARTIAL,
    "metadata": CapabilityLevel.PARTIAL,
    "audio": CapabilityLevel.WEAK,
    "audio_analysis": CapabilityLevel.WEAK,
    "video": CapabilityLevel.WEAK,
    "video_analysis": CapabilityLevel.WEAK,
    "dataset": CapabilityLevel.PARTIAL,
    "mixed": CapabilityLevel.PARTIAL,
    "transcript": CapabilityLevel.PARTIAL,
    "cad": CapabilityLevel.NONE,
}


def describe_capability(level: CapabilityLevel) -> str:
    if level >= CapabilityLevel.STRONG:
        return "strong"
    if level == CapabilityLevel.PARTIAL:
        return "partial"
    if level == CapabilityLevel.WEAK:
        return "weak"
    return "unsupported"
