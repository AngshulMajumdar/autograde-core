from __future__ import annotations

from typing import Any, Dict, List

from autograde.models import Submission


def detect_submission_failures(submission: Submission) -> List[Dict[str, Any]]:
    failures: List[Dict[str, Any]] = []

    if not submission.artifacts:
        failures.append({
            "type": "empty_submission",
            "severity": "critical",
            "reason": "Submission contains no artifacts.",
        })
        return failures

    if not submission.evidence:
        failures.append({
            "type": "no_evidence_extracted",
            "severity": "high",
            "reason": "No evidence could be extracted from the submission artifacts.",
        })

    execution_summary = submission.submission_metadata.get("execution_probe_summary", {})
    if execution_summary:
        tests_run = int(execution_summary.get("tests_run", 0) or 0)
        tests_passed = int(execution_summary.get("tests_passed", 0) or 0)
        if tests_run > 0 and tests_passed == 0:
            failures.append({
                "type": "non_executable_or_failing_code",
                "severity": "high",
                "reason": "Execution probes ran but no tests passed.",
            })

    warnings = list(submission.manifest.extraction_warnings)
    if warnings:
        failures.append({
            "type": "extraction_warnings_present",
            "severity": "medium",
            "reason": f"Extraction warnings detected: {len(warnings)}.",
        })

    text_claimy = any(ev.modality == "text" and ("claim" in ev.subtype or "result" in (ev.subtype or "")) for ev in submission.evidence)
    nontext_support = any(ev.modality in {"table", "execution", "diagram", "code"} for ev in submission.evidence)
    if text_claimy and not nontext_support:
        failures.append({
            "type": "unsupported_claims",
            "severity": "medium",
            "reason": "The submission makes claims but lacks supporting non-text evidence.",
        })

    return failures
