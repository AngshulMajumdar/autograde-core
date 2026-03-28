from __future__ import annotations

from pathlib import Path
from typing import List
import re

from PIL import Image, ImageFilter, ImageOps
import pytesseract

from autograde.plot import PlotAnalyzer
from autograde.diagram import DiagramAnalyzer

from autograde.extractors.base import BaseExtractor
from autograde.models import Artifact, EvidenceObject, Location


class ImageMetadataExtractor(BaseExtractor):
    extractor_id = "image_metadata_extractor_v3"
    supported_types = {"image", "design_diagram"}

    @staticmethod
    def _preprocess_variants(img: Image.Image) -> list[tuple[str, Image.Image]]:
        gray = ImageOps.grayscale(img)
        if max(gray.size) < 1200:
            scale = 2
            gray = gray.resize((gray.size[0] * scale, gray.size[1] * scale))
        contrast = ImageOps.autocontrast(gray)
        binary = contrast.point(lambda x: 255 if x > 170 else 0, mode="1").convert("L")
        sharpened = contrast.filter(ImageFilter.SHARPEN)
        return [("raw", img), ("gray", contrast), ("binary", binary), ("sharp", sharpened)]

    @staticmethod
    def _ocr_with_fallbacks(img: Image.Image) -> tuple[str, float, str]:
        configs = [
            ("--oem 3 --psm 6", 0.0),
            ("--oem 3 --psm 11", 0.0),
            ("--oem 3 --psm 4", 0.0),
        ]
        best_text, best_score, best_variant = "", 0.0, ""
        for variant_name, variant in ImageMetadataExtractor._preprocess_variants(img):
            for config, _ in configs:
                try:
                    txt = pytesseract.image_to_string(variant, config=config) or ""
                except Exception:
                    txt = ""
                cleaned = " ".join(txt.split())
                if not cleaned:
                    continue
                score = min(0.94, 0.45 + len(cleaned) / 250.0)
                if any(sym in cleaned for sym in ["=", "+", "-", "\u2264", "\u2208", "=>"]):
                    score += 0.05
                if sum(ch.isalpha() for ch in cleaned) > 15:
                    score += 0.05
                if score > best_score:
                    best_text, best_score, best_variant = txt, min(score, 0.96), f"{variant_name}:{config}"
        return best_text, best_score, best_variant

    def extract(self, artifact: Artifact) -> List[EvidenceObject]:
        path = Path(artifact.storage_path)
        modality = "image" if artifact.artifact_type == "image" else "diagram"
        tags = [artifact.artifact_type]
        evidence: List[EvidenceObject] = []

        if path.suffix.lower() == ".svg":
            evidence.extend(self._extract_svg(artifact, path, tags))
        else:
            evidence.extend(self._extract_raster(artifact, path, modality, tags))
        return evidence

    def _extract_svg(self, artifact: Artifact, path: Path, tags: List[str]) -> List[EvidenceObject]:
        raw = path.read_text(encoding="utf-8", errors="ignore")
        lowered = raw.lower()
        components = []
        for token, label in [
            ("op_amp", "op_amp"), ("opamp", "op_amp"), ("resistor", "resistor"), ("capacitor", "capacitor"),
            ("inductor", "inductor"), ("feedback", "feedback_path"), ("input", "input_node"), ("output", "output_node"),
            ("ground", "ground"), ("summing", "summing_junction"), ("gate", "logic_gate"), ("transistor", "transistor"),
        ]:
            if token in lowered:
                components.append(label)
        labels = re.findall(r">\s*([A-Za-z][A-Za-z0-9_+\-]*)\s*<", raw)
        labels += re.findall(r"id=[\'\"]([^\'\"]+)[\'\"]", raw)
        labels = [x for x in labels if len(x) <= 24]
        family = "unknown"
        if "op_amp" in components and "feedback_path" in components and "input_node" in components and "output_node" in components:
            family = "op_amp_feedback_family"
        if "lowpass" in lowered or ("capacitor" in components and "resistor" in components and "op_amp" in components):
            family = "active_filter_family" if family == "unknown" else family
        if "logic_gate" in components:
            family = "logic_family" if family == "unknown" else family
        plausible = int(("input_node" in components and "output_node" in components) or len(components) >= 2)
        line_like = len(re.findall(r"<(line|polyline|path|rect|circle)", lowered))
        topology = {
            "node_count_estimate": max(len(set(labels)), len(set(components))),
            "edge_count_estimate": line_like,
            "has_feedback": "feedback_path" in components,
            "component_count": len(set(components)),
            "diagram_family": family,
        }
        relation_analysis = DiagramAnalyzer().analyze_svg(raw)
        relation_graph = relation_analysis.get("graph", {})
        topology.update({
            "relation_node_count": int(relation_graph.get("node_count", 0) or 0),
            "relation_edge_count": int(relation_graph.get("edge_count", 0) or 0),
            "relation_types": relation_graph.get("relation_types", []),
        })
        common_tags = list(dict.fromkeys(tags + sorted(set(components)) + ([family] if family != "unknown" else [])))
        return [
            EvidenceObject(
                evidence_id=f"{artifact.artifact_id}_img_1",
                submission_id=artifact.submission_id,
                artifact_id=artifact.artifact_id,
                modality="diagram",
                subtype=artifact.artifact_type,
                content=raw[:4000],
                structured_content={
                    "file_suffix": path.suffix.lower(),
                    "detected_components": sorted(set(components)),
                    "detected_labels": sorted(set(labels[:20])),
                    "diagram_family": family,
                    "functional_plausibility": plausible,
                    "raw_text_length": len(raw),
                },
                preview=path.name,
                location=Location(file=path.name),
                confidence=0.8,
                extractor_id=self.extractor_id,
                tags=common_tags,
            ),
            EvidenceObject(
                evidence_id=f"{artifact.artifact_id}_topology_1",
                submission_id=artifact.submission_id,
                artifact_id=artifact.artifact_id,
                modality="diagram",
                subtype="topology",
                content=None,
                structured_content=topology,
                preview=f"topology:{family}",
                location=Location(file=path.name),
                confidence=0.72,
                extractor_id=self.extractor_id,
                tags=common_tags + ["topology"],
            ),
            EvidenceObject(
                evidence_id=f"{artifact.artifact_id}_relations_1",
                submission_id=artifact.submission_id,
                artifact_id=artifact.artifact_id,
                modality="diagram",
                subtype="relation_graph",
                content=None,
                structured_content=relation_graph,
                preview=f"relations:{relation_graph.get('family','generic_diagram')}",
                location=Location(file=path.name),
                confidence=0.74 if relation_graph.get("edge_count") else 0.62,
                extractor_id=self.extractor_id,
                tags=common_tags + ["relation_graph"],
            ),
        ]

    def _extract_raster(self, artifact: Artifact, path: Path, modality: str, tags: List[str]) -> List[EvidenceObject]:
        img = Image.open(path)
        width, height = img.size
        ocr_text, ocr_conf, ocr_variant = self._ocr_with_fallbacks(img)
        lowered = ocr_text.lower()
        metric_hits = {}
        for metric in ["accuracy", "acc", "loss", "precision", "recall", "f1", "gain", "cutoff", "bandwidth", "latency", "phase_margin", "ber", "snr"]:
            m = re.search(rf"{metric}[^0-9]{{0,10}}([0-9]+(?:\.[0-9]+)?%?)", lowered)
            if m:
                metric_hits[metric] = m.group(1)
        analysis_type = "image"
        if any(k in lowered for k in ["epoch", "accuracy", "loss", "time", "gain", "cutoff", "voltage", "frequency", "snr", "ber"]):
            analysis_type = "plot"
        elif any(k in path.stem.lower() for k in ["plot", "figure", "graph", "curve", "spectrum", "waveform"]):
            analysis_type = "plot"
        axis_tokens = [tok for tok in ["x", "y", "epoch", "time", "accuracy", "loss", "gain", "frequency", "voltage", "current", "snr", "ber"] if tok in lowered]
        plot_analysis = None
        diagram_analysis = None
        if analysis_type == "plot":
            try:
                plot_analysis = PlotAnalyzer().analyze(img)
            except Exception:
                plot_analysis = None
        elif modality == "diagram" or any(k in path.stem.lower() for k in ["uml", "timing", "block", "architecture", "diagram", "flow"]):
            try:
                diagram_analysis = DiagramAnalyzer().analyze(img)
            except Exception:
                diagram_analysis = None
        base = EvidenceObject(
            evidence_id=f"{artifact.artifact_id}_img_1",
            submission_id=artifact.submission_id,
            artifact_id=artifact.artifact_id,
            modality=modality,
            subtype=analysis_type,
            content=ocr_text[:4000] if ocr_text else None,
            structured_content={
                "file_suffix": path.suffix.lower(),
                "width": width,
                "height": height,
                "analysis_type": analysis_type,
                "ocr_text_present": bool(ocr_text.strip()),
                "ocr_variant": ocr_variant,
                "axis_tokens": axis_tokens,
                "detected_metrics": metric_hits,
                "plot_analysis": plot_analysis or {},
                "diagram_analysis": (diagram_analysis or {}).get("graph", {}),
            },
            preview=path.name,
            location=Location(file=path.name),
            confidence=0.88 if analysis_type == "plot" else 0.9,
            extractor_id=self.extractor_id,
            tags=tags + ([analysis_type] if analysis_type else []),
        )
        evidence = [base]
        if plot_analysis is not None:
            evidence.append(
                EvidenceObject(
                    evidence_id=f"{artifact.artifact_id}_plot_1",
                    submission_id=artifact.submission_id,
                    artifact_id=artifact.artifact_id,
                    modality="plot",
                    subtype="plot_analysis",
                    content=ocr_text[:4000] if ocr_text else None,
                    structured_content=plot_analysis,
                    preview=f"plot:{path.name}",
                    location=Location(file=path.name),
                    confidence=0.76 if plot_analysis.get("curves") else 0.62,
                    extractor_id=self.extractor_id,
                    tags=tags + ["plot_analysis"],
                )
            )
        if diagram_analysis is not None:
            relation_graph = (diagram_analysis or {}).get("graph", {})
            evidence.append(
                EvidenceObject(
                    evidence_id=f"{artifact.artifact_id}_relations_1",
                    submission_id=artifact.submission_id,
                    artifact_id=artifact.artifact_id,
                    modality="diagram",
                    subtype="relation_graph",
                    content=ocr_text[:4000] if ocr_text else None,
                    structured_content=relation_graph,
                    preview=f"relations:{relation_graph.get('family','generic_diagram')}",
                    location=Location(file=path.name),
                    confidence=0.74 if relation_graph.get("edge_count") else 0.6,
                    extractor_id=self.extractor_id,
                    tags=tags + ["relation_graph"],
                )
            )
        if ocr_text.strip():
            evidence.append(
                EvidenceObject(
                    evidence_id=f"{artifact.artifact_id}_ocr_1",
                    submission_id=artifact.submission_id,
                    artifact_id=artifact.artifact_id,
                    modality="text",
                    subtype="ocr_text",
                    content=ocr_text,
                    structured_content={"source_artifact_type": artifact.artifact_type, "analysis_type": analysis_type},
                    preview=ocr_text[:120],
                    location=Location(file=path.name),
                    confidence=ocr_conf,
                    extractor_id=self.extractor_id,
                    tags=tags + ["ocr"],
                )
            )
        return evidence