from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List

from autograde.extractors.base import BaseExtractor
from autograde.models import Artifact, EvidenceObject, Location


class NotebookExtractor(BaseExtractor):
    extractor_id = "notebook_extractor_v2"
    supported_types = {"notebook"}

    def extract(self, artifact: Artifact) -> List[EvidenceObject]:
        data = json.loads(self.read_text(artifact.storage_path))
        file_name = Path(artifact.storage_path).name
        evidence: List[EvidenceObject] = []
        code_cells = 0
        markdown_cells = 0
        output_cells = 0
        import_count = 0
        execution_orders = []
        transitions = []
        prev_type = None
        for idx, cell in enumerate(data.get("cells", []), start=1):
            source = "".join(cell.get("source", []))
            cell_type = cell.get("cell_type", "unknown")
            modality = "code" if cell_type == "code" else "text"
            subtype = f"notebook_{cell_type}"
            if cell_type == "code":
                code_cells += 1
                import_count += len(re.findall(r"^\s*(?:import|from)\s+", source, flags=re.MULTILINE))
                if cell.get("outputs"):
                    output_cells += 1
            elif cell_type == "markdown":
                markdown_cells += 1
            ex_count = cell.get("execution_count")
            if ex_count is not None:
                execution_orders.append(ex_count)
            if prev_type is not None:
                transitions.append(f"{prev_type}->{cell_type}")
            prev_type = cell_type
            evidence.append(
                EvidenceObject(
                    evidence_id=f"{artifact.artifact_id}_cell_{idx}",
                    submission_id=artifact.submission_id,
                    artifact_id=artifact.artifact_id,
                    modality=modality,
                    subtype=subtype,
                    content=source,
                    structured_content={"cell_type": cell_type, "execution_count": ex_count},
                    preview=source[:120],
                    location=Location(file=file_name, cell_index=idx),
                    confidence=0.99,
                    extractor_id=self.extractor_id,
                    tags=["notebook_cell"],
                )
            )
        execution_monotonic = execution_orders == sorted(execution_orders)
        has_narrative = markdown_cells > 0 and code_cells > 0
        evidence.append(
            EvidenceObject(
                evidence_id=f"{artifact.artifact_id}_flow_1",
                submission_id=artifact.submission_id,
                artifact_id=artifact.artifact_id,
                modality="metadata",
                subtype="notebook_flow",
                content=None,
                structured_content={
                    "code_cells": code_cells,
                    "markdown_cells": markdown_cells,
                    "output_cells": output_cells,
                    "import_count": import_count,
                    "execution_monotonic": execution_monotonic,
                    "has_narrative": has_narrative,
                    "transition_counts": {t: transitions.count(t) for t in sorted(set(transitions))},
                },
                preview=f"flow code={code_cells} markdown={markdown_cells}",
                location=Location(file=file_name),
                confidence=0.96,
                extractor_id=self.extractor_id,
                tags=["notebook", "flow_analysis"],
            )
        )
        return evidence
