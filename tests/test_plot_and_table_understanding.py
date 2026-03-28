from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from autograde.extractors.image_extractors import ImageMetadataExtractor
from autograde.extractors.tabular_extractors import CSVTableExtractor
from autograde.models import Artifact
from autograde.evaluators.registry import EvaluatorRegistry
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


def test_plot_analysis_and_observation_table(tmp_path: Path):
    img = Image.new("RGB", (320, 220), "white")
    d = ImageDraw.Draw(img)
    d.line((40, 180, 280, 180), fill="black", width=3)
    d.line((40, 180, 40, 30), fill="black", width=3)
    d.line((50, 160, 120, 120), fill="black", width=2)
    d.line((120, 120, 200, 90), fill="black", width=2)
    d.text((8, 10), "gain")
    d.text((230, 188), "frequency")
    plot_path = tmp_path / "gain_plot.png"
    img.save(plot_path)

    csv_path = tmp_path / "obs.csv"
    csv_path.write_text("trial,expected,measured\n1,5.0,4.8\n2,5.0,5.1\n3,5.0,4.9\n", encoding="utf-8")

    image_artifact = _artifact(tmp_path, "gain_plot.png", "image", "image/png")
    table_artifact = _artifact(tmp_path, "obs.csv", "spreadsheet", "text/csv")

    image_evidence = ImageMetadataExtractor().extract(image_artifact)
    table_evidence = CSVTableExtractor().extract(table_artifact)

    plot_items = [e for e in image_evidence if e.modality == "plot"]
    obs_items = [e for e in table_evidence if e.subtype in {"observation_sheet", "observation_summary"}]

    assert plot_items, "Expected dedicated plot evidence"
    assert obs_items, "Expected observation sheet evidence"

    criterion = Criterion(criterion_id="C1", name="plots", description="", max_score=10.0, weight=1.0, required_modalities=["plot"], evaluation_dimensions=["clarity"])
    registry = EvaluatorRegistry()
    plot_result = registry.get("plot_interpretation").evaluate(criterion, image_evidence)
    obs_result = registry.get("observation_sheet_understanding").evaluate(criterion, table_evidence)

    assert plot_result.score > 0
    assert obs_result.score > 0
    assert table_evidence[0].structured_content["table_kind"] == "observation_sheet"
