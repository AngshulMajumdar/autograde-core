from __future__ import annotations

import ast
import io
import tokenize
from pathlib import Path
from typing import List

from autograde.extractors.base import BaseExtractor
from autograde.models import Artifact, EvidenceObject, Location


class PythonCodeExtractor(BaseExtractor):
    extractor_id = "python_code_extractor_v2"
    supported_types = {"source_code"}

    def extract(self, artifact: Artifact) -> List[EvidenceObject]:
        source = self.read_text(artifact.storage_path)
        file_name = Path(artifact.storage_path).name
        evidence: List[EvidenceObject] = []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            evidence.append(
                EvidenceObject(
                    evidence_id=f"{artifact.artifact_id}_code_file",
                    submission_id=artifact.submission_id,
                    artifact_id=artifact.artifact_id,
                    modality="code",
                    subtype="file",
                    content=source,
                    structured_content={"parse_error": True, "function_count": 0},
                    preview=source[:120],
                    location=Location(file=file_name, line_start=1),
                    confidence=0.55,
                    extractor_id=self.extractor_id,
                    tags=["raw_code", "parse_error"],
                )
            )
            return evidence

        function_defs = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        class_defs = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        import_nodes = [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]
        loop_nodes = [node for node in ast.walk(tree) if isinstance(node, (ast.For, ast.While))]
        conditional_nodes = [node for node in ast.walk(tree) if isinstance(node, ast.If)]
        docstring = ast.get_docstring(tree)
        comment_lines = self._count_comment_lines(source)

        evidence.append(
            EvidenceObject(
                evidence_id=f"{artifact.artifact_id}_code_file",
                submission_id=artifact.submission_id,
                artifact_id=artifact.artifact_id,
                modality="code",
                subtype="file",
                content=source,
                structured_content={
                    "parse_error": False,
                    "function_count": len(function_defs),
                    "class_count": len(class_defs),
                    "import_count": len(import_nodes),
                    "loop_count": len(loop_nodes),
                    "conditional_count": len(conditional_nodes),
                    "line_count": len(source.splitlines()),
                    "comment_line_count": comment_lines,
                    "has_module_docstring": bool(docstring),
                },
                preview=source[:120],
                location=Location(file=file_name, line_start=1, line_end=max(1, len(source.splitlines()))),
                confidence=0.99,
                extractor_id=self.extractor_id,
                tags=["raw_code", "code_file"],
            )
        )

        for idx, node in enumerate(function_defs, start=1):
            snippet = ast.get_source_segment(source, node) or f"def {node.name}(...)"
            evidence.append(
                EvidenceObject(
                    evidence_id=f"{artifact.artifact_id}_fn_{idx}",
                    submission_id=artifact.submission_id,
                    artifact_id=artifact.artifact_id,
                    modality="code",
                    subtype="function",
                    content=snippet,
                    structured_content={
                        "function_name": node.name,
                        "arg_count": len(node.args.args),
                        "line_count": len(snippet.splitlines()),
                        "has_docstring": bool(ast.get_docstring(node)),
                    },
                    preview=snippet.splitlines()[0][:120],
                    location=Location(file=file_name, line_start=node.lineno, line_end=getattr(node, "end_lineno", node.lineno)),
                    confidence=0.99,
                    extractor_id=self.extractor_id,
                    tags=["function", node.name.lower()],
                )
            )

        return evidence

    @staticmethod
    def _count_comment_lines(source: str) -> int:
        count = 0
        try:
            for tok in tokenize.generate_tokens(io.StringIO(source).readline):
                if tok.type == tokenize.COMMENT:
                    count += 1
        except tokenize.TokenError:
            return count
        return count
