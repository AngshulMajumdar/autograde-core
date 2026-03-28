from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import List

from autograde.models import Artifact


@dataclass(slots=True)
class CallableUnit:
    artifact_id: str
    file_path: str
    file_name: str
    function_name: str
    line_start: int
    line_end: int
    source: str


class CallableRecovery:
    """Recover callable functions from Python source artifacts."""

    def recover(self, artifacts: list[Artifact]) -> List[CallableUnit]:
        units: list[CallableUnit] = []
        for artifact in artifacts:
            if artifact.artifact_type != "source_code" or not artifact.storage_path.endswith(".py"):
                continue
            path = Path(artifact.storage_path)
            try:
                source = path.read_text(encoding="utf-8")
                tree = ast.parse(source)
            except Exception:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    snippet = ast.get_source_segment(source, node) or f"def {node.name}(...): pass"
                    units.append(
                        CallableUnit(
                            artifact_id=artifact.artifact_id,
                            file_path=str(path),
                            file_name=path.name,
                            function_name=node.name,
                            line_start=node.lineno,
                            line_end=getattr(node, "end_lineno", node.lineno),
                            source=snippet,
                        )
                    )
        return units
