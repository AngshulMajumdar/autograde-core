from __future__ import annotations

import csv
import math
from pathlib import Path
from statistics import mean
from typing import List

from autograde.extractors.base import BaseExtractor
from autograde.models import Artifact, EvidenceObject, Location


_METRIC_NAMES = {
    "accuracy", "precision", "recall", "f1", "error", "loss", "gain", "cutoff", "bandwidth",
    "phase_margin", "stability", "voltage", "current", "time", "frequency", "snr", "ber"
}
_OBSERVATION_HINTS = {
    "observed", "measured", "expected", "theoretical", "reading", "trial", "experiment", "sample"
}


class CSVTableExtractor(BaseExtractor):
    extractor_id = "csv_table_extractor_v2"
    supported_types = {"spreadsheet"}

    def extract(self, artifact: Artifact) -> List[EvidenceObject]:
        path = Path(artifact.storage_path)
        with path.open("r", encoding="utf-8", errors="ignore", newline="") as fh:
            reader = list(csv.reader(fh))
        preview = " | ".join(reader[0]) if reader else ""
        header = [str(h).strip() for h in (reader[0] if reader else [])]
        data_rows = reader[1:] if len(reader) > 1 else []
        numeric_summary = self._numeric_summary(header, data_rows)
        table_kind = self._classify_table(header)
        observation_summary = self._observation_summary(header, data_rows, numeric_summary) if table_kind == "observation_sheet" else {}
        csv_text = "\n".join([", ".join(row) for row in reader[:30]])
        evidence = [
            EvidenceObject(
                evidence_id=f"{artifact.artifact_id}_table_1",
                submission_id=artifact.submission_id,
                artifact_id=artifact.artifact_id,
                modality="table",
                subtype=table_kind,
                content=csv_text,
                structured_content={
                    "rows": len(reader),
                    "cols": len(reader[0]) if reader else 0,
                    "header": header,
                    "numeric_metrics": numeric_summary,
                    "metrics": numeric_summary,
                    "table_kind": table_kind,
                    "observation_summary": observation_summary,
                },
                preview=preview[:120],
                location=Location(file=path.name),
                confidence=0.99,
                extractor_id=self.extractor_id,
                tags=["table", table_kind],
            )
        ]
        if observation_summary:
            evidence.append(
                EvidenceObject(
                    evidence_id=f"{artifact.artifact_id}_obs_1",
                    submission_id=artifact.submission_id,
                    artifact_id=artifact.artifact_id,
                    modality="table",
                    subtype="observation_summary",
                    content=None,
                    structured_content=observation_summary,
                    preview=f"observation:{path.name}",
                    location=Location(file=path.name),
                    confidence=0.94,
                    extractor_id=self.extractor_id,
                    tags=["table", "observation_sheet", "summary"],
                )
            )
        return evidence

    def _classify_table(self, header: list[str]) -> str:
        lowered = {h.lower() for h in header}
        if lowered & _OBSERVATION_HINTS or {"expected", "theoretical"} & lowered:
            return "observation_sheet"
        if lowered & _METRIC_NAMES:
            return "results_table"
        return "csv_table"

    def _numeric_summary(self, header: list[str], data_rows: list[list[str]]) -> dict:
        summary = {}
        for col_idx, name in enumerate(header):
            lname = name.lower()
            values = []
            for row in data_rows:
                if col_idx >= len(row):
                    continue
                raw = str(row[col_idx]).strip().replace('%', '')
                try:
                    values.append(float(raw))
                except ValueError:
                    continue
            if not values:
                continue
            col_summary = {
                "count": len(values),
                "mean": mean(values),
                "min": min(values),
                "max": max(values),
            }
            if lname in _METRIC_NAMES:
                summary[lname] = col_summary["mean"]
            summary[f"{lname}__summary"] = col_summary
        return summary

    def _observation_summary(self, header: list[str], data_rows: list[list[str]], numeric_summary: dict) -> dict:
        lowered = [h.lower() for h in header]
        expected_idx = next((i for i, h in enumerate(lowered) if h in {"expected", "theoretical"}), None)
        measured_idx = next((i for i, h in enumerate(lowered) if h in {"measured", "observed", "reading"}), None)
        trial_idx = next((i for i, h in enumerate(lowered) if h in {"trial", "experiment", "sample"}), None)
        comparison_rows = []
        deviations = []
        if expected_idx is not None and measured_idx is not None:
            for row in data_rows:
                if max(expected_idx, measured_idx) >= len(row):
                    continue
                try:
                    exp_v = float(str(row[expected_idx]).strip().replace('%', ''))
                    meas_v = float(str(row[measured_idx]).strip().replace('%', ''))
                except ValueError:
                    continue
                dev = meas_v - exp_v
                deviations.append(dev)
                label = row[trial_idx] if trial_idx is not None and trial_idx < len(row) else str(len(comparison_rows) + 1)
                comparison_rows.append({"trial": label, "expected": exp_v, "measured": meas_v, "deviation": dev})
        return {
            "trial_count": len(data_rows),
            "has_expected_measured_pairs": bool(comparison_rows),
            "avg_abs_deviation": mean(abs(d) for d in deviations) if deviations else None,
            "comparison_rows": comparison_rows[:20],
            "numeric_summary": numeric_summary,
        }
