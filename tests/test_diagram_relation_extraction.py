from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from autograde.extractors.image_extractors import ImageMetadataExtractor
from autograde.evaluators.registry import EvaluatorRegistry
from autograde.models import Artifact
from autograde.rubric import Criterion


def _artifact(tmp_path: Path, name: str, artifact_type: str, mime: str) -> Artifact:
    path = tmp_path / name
    return Artifact(
        artifact_id=f"a_{name}",
        submission_id="sub1",
        file_name=name,
        artifact_type=artifact_type,
        mime_type=mime,
        storage_path=str(path),
        checksum="x",
        size_bytes=path.stat().st_size,
    )


def test_svg_relation_graph_extraction(tmp_path: Path):
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="300" height="120">
      <text x="20" y="20">Controller</text>
      <line x1="90" y1="18" x2="160" y2="18" stroke="black" />
      <text x="170" y="20">Service</text>
      <line x1="220" y1="18" x2="280" y2="18" stroke="black" />
      <text x="285" y="20">Repository</text>
    </svg>'''
    path = tmp_path / "uml.svg"
    path.write_text(svg, encoding="utf-8")
    artifact = _artifact(tmp_path, "uml.svg", "design_diagram", "image/svg+xml")
    evidence = ImageMetadataExtractor().extract(artifact)
    rel = [e for e in evidence if e.subtype == "relation_graph"]
    assert rel, "Expected relation graph evidence"
    graph = rel[0].structured_content
    assert graph["node_count"] >= 3
    assert graph["edge_count"] >= 2
    assert graph["family"] in {"uml_or_architecture", "generic_diagram"}


def test_timing_relation_graph_affects_evaluator(tmp_path: Path):
    img = Image.new("RGB", (320, 140), "white")
    d = ImageDraw.Draw(img)
    d.line((20, 30, 120, 30), fill="black", width=2)
    d.line((120, 30, 120, 80), fill="black", width=2)
    d.line((120, 80, 220, 80), fill="black", width=2)
    d.text((8, 18), "CLK")
    d.text((130, 68), "Q")
    d.text((230, 68), "RESET")
    path = tmp_path / "timing.png"
    img.save(path)
    artifact = _artifact(tmp_path, "timing.png", "design_diagram", "image/png")
    evidence = ImageMetadataExtractor().extract(artifact)
    rel = [e for e in evidence if e.subtype == "relation_graph"]
    assert rel, "Expected raster relation graph evidence"
    criterion = Criterion(
        criterion_id="C1",
        name="timing",
        description="",
        max_score=10.0,
        weight=1.0,
        required_modalities=["diagram"],
        evaluation_dimensions=["correctness"],
    )
    result = EvaluatorRegistry().get("timing_diagram_correctness").evaluate(criterion, evidence)
    assert result.score > 0
    assert any(e.evidence_id.endswith("relations_1") for e in rel)
