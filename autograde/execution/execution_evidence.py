from __future__ import annotations

from typing import List

from autograde.execution.callable_recovery import CallableUnit
from autograde.execution.unit_probe_runner import ProbeResult
from autograde.models import EvidenceLink, EvidenceObject, Location


def probe_results_to_evidence(submission_id: str, units: list[CallableUnit], results: list[ProbeResult]) -> List[EvidenceObject]:
    unit_map = {(u.artifact_id, u.function_name): u for u in units}
    evidence: list[EvidenceObject] = []
    for idx, result in enumerate(results, start=1):
        unit = unit_map.get((result.artifact_id, result.function_name))
        tests_run = max(result.tests_run, 0)
        tests_passed = max(result.tests_passed, 0)
        confidence = 0.95 if result.status == "ok" else 0.75 if result.status == "exception" else 0.65
        tags = ["execution_probe", result.function_name.lower(), result.probe_kind]
        if tests_run and tests_passed == tests_run:
            tags.append("behavior_verified")
        elif tests_run and tests_passed < tests_run:
            tags.append("behavior_partial")
        else:
            tags.append("behavior_unverified")
        linked: list[EvidenceLink] = []
        if unit:
            linked.append(EvidenceLink(type="implements", target=f"{unit.artifact_id}_code_file"))
        evidence.append(
            EvidenceObject(
                evidence_id=f"{result.artifact_id}_exec_{idx}",
                submission_id=submission_id,
                artifact_id=result.artifact_id,
                modality="execution",
                subtype="unit_test_result",
                content=result.rationale,
                structured_content={
                    "function_name": result.function_name,
                    "probe_kind": result.probe_kind,
                    "status": result.status,
                    "tests_run": tests_run,
                    "tests_passed": tests_passed,
                    "pass_rate": (tests_passed / tests_run) if tests_run else 0.0,
                    "test_details": result.test_details,
                },
                preview=result.rationale[:160],
                location=Location(file=unit.file_name if unit else None, line_start=unit.line_start if unit else None, line_end=unit.line_end if unit else None),
                confidence=confidence,
                extractor_id="unit_probe_runner_v1",
                tags=tags,
                links=linked,
            )
        )
    return evidence
