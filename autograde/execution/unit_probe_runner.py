from __future__ import annotations

from dataclasses import dataclass
from typing import List

from autograde.execution.callable_recovery import CallableUnit
from autograde.execution.sandbox_runner import SandboxRunner


@dataclass(slots=True)
class ProbeResult:
    artifact_id: str
    file_path: str
    function_name: str
    probe_kind: str
    status: str
    tests_run: int
    tests_passed: int
    rationale: str
    test_details: list[dict]


class UnitProbeRunner:
    def __init__(self, timeout_seconds: int = 3) -> None:
        self.sandbox = SandboxRunner(timeout_seconds=timeout_seconds)

    def run(self, units: List[CallableUnit]) -> List[ProbeResult]:
        results: list[ProbeResult] = []
        for unit in units:
            probe_kind = self._infer_probe_kind(unit.function_name)
            payload = self.sandbox.run_probe(unit.file_path, unit.function_name, probe_kind)
            results.append(
                ProbeResult(
                    artifact_id=unit.artifact_id,
                    file_path=unit.file_path,
                    function_name=unit.function_name,
                    probe_kind=probe_kind,
                    status=str(payload.get("status", "error")),
                    tests_run=int(payload.get("tests_run", 0) or 0),
                    tests_passed=int(payload.get("tests_passed", 0) or 0),
                    rationale=str(payload.get("rationale", "")),
                    test_details=list(payload.get("test_details", [])),
                )
            )
        return results

    @staticmethod
    def _infer_probe_kind(function_name: str) -> str:
        name = function_name.lower()
        if "dijkstra" in name:
            return "dijkstra"
        if name == "bfs" or "breadth" in name:
            return "bfs"
        return "generic"
