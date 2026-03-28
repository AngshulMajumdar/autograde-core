from __future__ import annotations

from autograde.execution.callable_recovery import CallableRecovery
from autograde.execution.execution_evidence import probe_results_to_evidence
from autograde.execution.unit_probe_runner import UnitProbeRunner
from autograde.models import Submission


class CodeExecutionProbeEngine:
    def __init__(self) -> None:
        self.recovery = CallableRecovery()
        self.runner = UnitProbeRunner(timeout_seconds=3)

    def attach_execution_evidence(self, submission: Submission) -> int:
        if any(e.extractor_id == "unit_probe_runner_v1" for e in submission.evidence):
            return 0
        units = self.recovery.recover(submission.artifacts)
        if not units:
            return 0
        results = self.runner.run(units)
        evidence = probe_results_to_evidence(submission.submission_id, units, results)
        for ev in evidence:
            submission.add_evidence(ev)
        submission.submission_metadata["execution_probe_summary"] = {
            "callable_units": len(units),
            "probe_results": len(results),
            "tests_run": sum(ev.structured_content.get("tests_run", 0) for ev in evidence),
            "tests_passed": sum(ev.structured_content.get("tests_passed", 0) for ev in evidence),
        }
        return len(evidence)
