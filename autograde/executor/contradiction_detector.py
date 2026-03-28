from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence

from autograde.executor.claim_graph import ClaimGraph
from autograde.executor.claims import Claim, ClaimExtractor
from autograde.executor.evidence_query import EvidenceBundle
from autograde.executor.normalization import ClaimNormalizer
from autograde.models import EvidenceObject
from autograde.rubric import Criterion


@dataclass(slots=True)
class ContradictionResult:
    contradiction_type: str
    passed: bool
    confidence: float
    rationale: str
    evidence_ids: List[str] = field(default_factory=list)
    flags: List[Dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class ContradictionReport:
    contradictions: List[ContradictionResult] = field(default_factory=list)
    severity: str = "none"
    confidence: float = 0.0
    rationale: str = ""
    flags: List[Dict[str, Any]] = field(default_factory=list)


class ContradictionDetector:
    def __init__(self) -> None:
        self.claims = ClaimExtractor()
        self.normalizer = ClaimNormalizer()

    def detect(self, criterion: Criterion, evidence_bundle: EvidenceBundle, claim_graph: ClaimGraph | None = None) -> ContradictionReport:
        evidence = list(evidence_bundle.evidence)
        if claim_graph is None:
            claims = self.claims.extract(evidence)
        else:
            claims = [
                Claim(
                    claim_type=node.claim_type,
                    subject=node.subject,
                    value=node.value,
                    evidence_id=node.evidence_id,
                    confidence=node.confidence,
                    raw_text=node.raw_text,
                )
                for node in claim_graph.claims_for_evidence_ids([e.evidence_id for e in evidence])
            ]
        results: List[ContradictionResult] = []
        results.extend(self._algorithm_contradictions(claims))
        results.extend(self._metric_contradictions(claims))
        results.extend(self._diagram_text_contradictions(claims, evidence))

        contradictions = [r for r in results if not r.passed]
        if not contradictions:
            return ContradictionReport(
                contradictions=[],
                severity="none",
                confidence=0.75 if claims else 0.4,
                rationale="No grading-relevant contradictions were detected.",
                flags=[],
            )

        flags = [flag for r in contradictions for flag in r.flags]
        high = any(flag.get("severity") == "high" for flag in flags)
        medium = any(flag.get("severity") == "medium" for flag in flags)
        severity = "high" if high else "medium" if medium else "low"
        confidence = max((r.confidence for r in contradictions), default=0.6)
        rationale = " ".join(r.rationale for r in contradictions)
        return ContradictionReport(
            contradictions=contradictions,
            severity=severity,
            confidence=round(confidence, 3),
            rationale=rationale,
            flags=flags,
        )

    def _algorithm_contradictions(self, claims: Sequence[Claim]) -> List[ContradictionResult]:
        text_algos = [c for c in claims if c.claim_type == "algorithm_claim"]
        code_algos = [c for c in claims if c.claim_type == "algorithm_fact"]
        if not text_algos or not code_algos:
            return []
        text_values = {str(self.normalizer.normalize_algorithm(str(c.value)).value) for c in text_algos}
        code_values = {str(self.normalizer.normalize_algorithm(str(c.value)).value) for c in code_algos}
        if text_values & code_values:
            return [ContradictionResult("algorithm_alignment", True, 0.82, "Algorithm claims matched code-level algorithm signals.")]
        ev_ids = [c.evidence_id for c in text_algos[:2]] + [c.evidence_id for c in code_algos[:2]]
        return [
            ContradictionResult(
                "algorithm_mismatch",
                False,
                0.84,
                f"The report claimed algorithm(s) {sorted(text_values)}, but code signals indicated {sorted(code_values)}.",
                evidence_ids=ev_ids,
                flags=[{"type": "contradiction", "subtype": "algorithm_mismatch", "severity": "high"}],
            )
        ]

    def _metric_contradictions(self, claims: Sequence[Claim]) -> List[ContradictionResult]:
        text_metrics = [c for c in claims if c.claim_type in {"metric_claim", "metric_threshold_claim"}]
        table_metrics = [c for c in claims if c.claim_type == "metric_fact"]
        results: List[ContradictionResult] = []
        if not text_metrics or not table_metrics:
            return results
        table_map = {c.subject: float(c.value) for c in table_metrics}
        table_ev_map = {c.subject: c.evidence_id for c in table_metrics}
        for claim in text_metrics:
            metric = claim.subject.split(":", 1)[0]
            if metric not in table_map:
                continue
            actual = table_map[metric]
            if claim.claim_type == "metric_claim":
                expected = float(claim.value)
                diff = abs(expected - actual)
                if diff > 0.05:
                    results.append(
                        ContradictionResult(
                            "metric_value_mismatch",
                            False,
                            0.88,
                            f"The submission text claimed {metric}={expected:.3f}, but the table reported {actual:.3f}.",
                            evidence_ids=[claim.evidence_id, table_ev_map.get(metric, "")],
                            flags=[{"type": "contradiction", "subtype": "metric_value_mismatch", "severity": "high", "metric": metric, "difference": round(diff, 3)}],
                        )
                    )
            else:
                op = claim.subject.split(":", 1)[1]
                expected = float(claim.value)
                violated = (op == ">" and actual <= expected) or (op == "<" and actual >= expected)
                if violated:
                    results.append(
                        ContradictionResult(
                            "metric_threshold_mismatch",
                            False,
                            0.86,
                            f"The submission text claimed {metric} {op} {expected:.3f}, but the table reported {actual:.3f}.",
                            evidence_ids=[claim.evidence_id, table_ev_map.get(metric, "")],
                            flags=[{"type": "contradiction", "subtype": "metric_threshold_mismatch", "severity": "high", "metric": metric}],
                        )
                    )
        return results

    def _diagram_text_contradictions(self, claims: Sequence[Claim], evidence: Sequence[EvidenceObject]) -> List[ContradictionResult]:
        text_chunks = [e for e in evidence if e.modality == "text" and e.content]
        has_feedback_diagram = any(c.claim_type == "diagram_fact" and c.subject == "feedback_loop" for c in claims)
        if not has_feedback_diagram or not text_chunks:
            return []
        joined = " ".join((e.content or "").lower() for e in text_chunks[:8])
        if has_feedback_diagram and any(term in joined for term in ["open loop", "open-loop", "no feedback"]):
            return [
                ContradictionResult(
                    "diagram_text_mismatch",
                    False,
                    0.73,
                    "The text simultaneously described an open-loop design while diagram evidence suggested a feedback loop.",
                    evidence_ids=[e.evidence_id for e in text_chunks[:2]],
                    flags=[{"type": "contradiction", "subtype": "diagram_text_mismatch", "severity": "medium"}],
                )
            ]
        return []
