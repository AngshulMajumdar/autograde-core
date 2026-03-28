from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Sequence

from autograde.models import EvidenceObject


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z_][a-zA-Z0-9_'-]*", text.lower()))


@dataclass(slots=True)
class CrossCheckResult:
    check_id: str
    passed: bool
    confidence: float
    rationale: str
    evidence_ids: List[str] = field(default_factory=list)
    flags: List[Dict[str, object]] = field(default_factory=list)


class CrossCheckEngine:
    def run(self, check_ids: Sequence[str], evidence: Sequence[EvidenceObject]) -> List[CrossCheckResult]:
        return [self._run_one(cid, evidence) for cid in check_ids]

    def _run_one(self, check_id: str, evidence: Sequence[EvidenceObject]) -> CrossCheckResult:
        texts = [e for e in evidence if e.modality == "text" and e.content]
        codes = [e for e in evidence if e.modality == "code" and e.content]
        images = [e for e in evidence if e.modality in {"image", "diagram"}]
        tables = [e for e in evidence if e.modality == "table"]

        if check_id == "report_matches_code":
            if not texts or not codes:
                return CrossCheckResult(check_id, False, 0.6, "Report-code cross-check could not run because one modality was missing.")
            text_tokens = set().union(*(_tokenize(e.content or "") for e in texts[:8]))
            code_tokens = set().union(*(_tokenize(e.content or "") for e in codes[:8]))
            overlap = len((text_tokens & code_tokens) - {"def", "return", "class", "import"})
            passed = overlap >= 3
            return CrossCheckResult(
                check_id,
                passed,
                0.74,
                f"Report-code cross-check found {overlap} overlapping technical tokens.",
                evidence_ids=[e.evidence_id for e in (texts[:2] + codes[:2])],
                flags=[] if passed else [{"type": "cross_check_failure", "check": check_id, "overlap": overlap}],
            )
        if check_id == "claims_match_figures":
            if not texts or not (images or tables):
                return CrossCheckResult(check_id, False, 0.55, "Claims-figures cross-check could not run because claims or result artifacts were missing.")
            joined = " ".join((e.content or "").lower() for e in texts[:8])
            claim_present = any(tok in joined for tok in ["result", "observed", "improved", "accuracy", "error", "table", "figure"])
            passed = claim_present and bool(images or tables)
            return CrossCheckResult(
                check_id,
                passed,
                0.68,
                "Claims-figures cross-check looked for result-language plus figures/tables.",
                evidence_ids=[e.evidence_id for e in (texts[:2] + images[:1] + tables[:1])],
                flags=[] if passed else [{"type": "cross_check_failure", "check": check_id}],
            )
        if check_id == "diagram_matches_text":
            if not texts or not images:
                return CrossCheckResult(check_id, False, 0.6, "Diagram-text cross-check could not run because one modality was missing.")
            text_tokens = set().union(*(_tokenize(e.content or "") for e in texts[:8]))
            labels = set()
            for e in images[:8]:
                labels.update(str(x).lower() for x in e.structured_content.get("detected_labels", []))
                labels.update(str(x).lower() for x in e.structured_content.get("detected_components", []))
            overlap = len(text_tokens & labels)
            passed = overlap >= 1 or bool(labels)
            return CrossCheckResult(
                check_id,
                passed,
                0.65,
                f"Diagram-text cross-check found {overlap} shared labels/components.",
                evidence_ids=[e.evidence_id for e in (texts[:2] + images[:2])],
                flags=[] if passed else [{"type": "cross_check_failure", "check": check_id, "overlap": overlap}],
            )
        return CrossCheckResult(check_id, True, 0.5, f"Unknown cross-check '{check_id}' was treated as advisory only.")
