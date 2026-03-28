from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Sequence

from autograde.executor.normalization import ClaimNormalizer
from autograde.models import EvidenceObject
from autograde.llm.claim_extractor import LLMClaimExtractor

_ALGO_NAMES = {
    "dijkstra", "bfs", "dfs", "bellman-ford", "bellman ford", "floyd-warshall", "floyd warshall",
    "a*", "astar", "kruskal", "prim",
}
_METRIC_NAMES = {"accuracy", "precision", "recall", "f1", "error", "loss", "gain", "cutoff", "bandwidth", "phase_margin", "stability"}
_METRIC_PATTERN = re.compile(
    r"\b(accuracy|precision|recall|f1|error|loss|gain|cutoff|bandwidth|phase_margin|stability)\b[^\d]{0,20}(\d+(?:\.\d+)?)\s*(%?)",
    re.IGNORECASE,
)
_THRESHOLD_PATTERN = re.compile(
    r"\b(accuracy|precision|recall|f1|error|loss|gain|cutoff|bandwidth|phase_margin|stability)\b[^\d]{0,20}(above|over|greater than|less than|below|under)\s*(\d+(?:\.\d+)?)\s*(%?)",
    re.IGNORECASE,
)
_COMPLEXITY_PATTERN = re.compile(r"o\(([^\)]+)\)", re.IGNORECASE)


@dataclass(slots=True)
class Claim:
    claim_type: str
    subject: str
    value: str | float
    evidence_id: str
    confidence: float
    raw_text: str
    source: str = 'heuristic'


class ClaimExtractor:
    """LLM-first claim extraction with deterministic heuristic fallback."""

    def __init__(
        self,
        use_llm: bool = True,
        heuristic_fallback: bool = True,
        min_confidence: float = 0.65,
        allow_text_heuristic_fallback: bool = True,
    ) -> None:
        self.normalizer = ClaimNormalizer()
        self.use_llm = use_llm
        self.heuristic_fallback = heuristic_fallback
        self.min_confidence = float(min_confidence)
        self.allow_text_heuristic_fallback = bool(allow_text_heuristic_fallback)
        self.llm_extractor = LLMClaimExtractor() if use_llm else None

    def extract(self, evidence: Sequence[EvidenceObject]) -> List[Claim]:
        llm_claims: List[Claim] = []
        llm_live = False
        if self.use_llm and self.llm_extractor is not None:
            try:
                raw_claims, llm_live = self.llm_extractor.extract(evidence)
                for item in raw_claims:
                    conf = float(item.get('confidence', 0.0))
                    if conf < self.min_confidence:
                        continue
                    llm_claims.append(Claim(
                        str(item.get('claim_type', 'claim')),
                        str(item.get('subject', 'unknown')),
                        item.get('value', ''),
                        str(item.get('evidence_id', '')),
                        conf,
                        str(item.get('raw_text', item.get('value', ''))),
                        str(item.get('source', 'llm')),
                    ))
            except Exception:
                llm_live = False
                llm_claims = []
        claims: List[Claim] = list(llm_claims)
        if self.heuristic_fallback and (not llm_live or not claims):
            for ev in evidence:
                if ev.modality == 'text' and ev.content and self.allow_text_heuristic_fallback:
                    claims.extend(self._extract_from_text(ev))
                elif ev.modality == 'code' and ev.content:
                    claims.extend(self._extract_from_code(ev))
                elif ev.modality == 'table':
                    claims.extend(self._extract_from_table(ev))
                elif ev.modality in {'diagram', 'image'}:
                    claims.extend(self._extract_from_diagram(ev))
        uniq: dict[tuple[str, str, str, str], Claim] = {}
        for c in claims:
            if c.confidence < self.min_confidence:
                continue
            key = (c.claim_type, c.subject, str(c.value), c.evidence_id)
            prev = uniq.get(key)
            if prev is None or c.confidence > prev.confidence:
                uniq[key] = c
        return list(uniq.values())

    def _extract_from_text(self, ev: EvidenceObject) -> List[Claim]:
        text = ev.content or ''
        lowered = text.lower()
        claims: List[Claim] = []
        algo_patterns = [
            r"implemented\s+([a-zA-Z*\- ]+?)\s+algorithm",
            r"uses?\s+([a-zA-Z*\- ]+?)\s+algorithm",
            r"applied\s+([a-zA-Z*\- ]+?)\s+algorithm",
            r"the\s+algorithm\s+is\s+([a-zA-Z*\- ]+?)(?:[\.,;]|$)",
        ]
        for pattern in algo_patterns:
            for match in re.finditer(pattern, lowered):
                algo = match.group(1).strip()
                if algo:
                    _, norm_algo = self.normalizer.normalize_claim('algorithm_claim', 'algorithm', algo, match.group(0))
                    claims.append(Claim('algorithm_claim', 'algorithm', norm_algo, ev.evidence_id, 0.68, match.group(0), 'heuristic'))
        for algo in _ALGO_NAMES:
            if algo in lowered and any(w in lowered for w in ['implemented', 'uses', 'algorithm', 'method']):
                _, norm_algo = self.normalizer.normalize_claim('algorithm_claim', 'algorithm', algo, text[:140])
                claims.append(Claim('algorithm_claim', 'algorithm', norm_algo, ev.evidence_id, 0.66, text[:140], 'heuristic'))
        for match in _METRIC_PATTERN.finditer(text):
            metric = self.normalizer.normalize_metric_name(match.group(1).lower())
            value = self.normalizer.normalize_numeric_value(match.group(2), raw_text=match.group(0) + match.group(3)).value
            claims.append(Claim('metric_claim', metric, value, ev.evidence_id, 0.72, match.group(0), 'heuristic'))
        for match in _THRESHOLD_PATTERN.finditer(text):
            metric = self.normalizer.normalize_metric_name(match.group(1).lower())
            op = match.group(2).lower().replace('greater than', '>').replace('less than', '<').replace('above', '>').replace('over', '>').replace('below', '<').replace('under', '<')
            value = self.normalizer.normalize_numeric_value(match.group(3), raw_text=match.group(0) + match.group(4)).value
            claims.append(Claim('metric_threshold_claim', f'{metric}:{op}', value, ev.evidence_id, 0.76, match.group(0), 'heuristic'))
        for match in _COMPLEXITY_PATTERN.finditer(lowered):
            _, norm_complexity = self.normalizer.normalize_claim('complexity_claim', 'complexity', match.group(0).lower(), match.group(0))
            claims.append(Claim('complexity_claim', 'complexity', norm_complexity, ev.evidence_id, 0.68, match.group(0), 'heuristic'))
        uniq = {}
        for c in claims:
            uniq[(c.claim_type, c.subject, str(c.value))] = c
        return list(uniq.values())

    def _extract_from_code(self, ev: EvidenceObject) -> List[Claim]:
        text = (ev.content or '').lower()
        claims: List[Claim] = []
        fn_name = str(ev.structured_content.get('function_name', '')).lower()
        if fn_name:
            claims.append(Claim('code_fact', 'function_name', fn_name, ev.evidence_id, 0.92, fn_name, 'heuristic'))
        for algo in _ALGO_NAMES:
            normalized = algo.replace(' ', '')
            if algo in text or normalized in text:
                _, norm_algo = self.normalizer.normalize_claim('algorithm_fact', 'algorithm', algo, algo)
                claims.append(Claim('algorithm_fact', 'algorithm', norm_algo, ev.evidence_id, 0.88, algo, 'heuristic'))
        if 'heapq' in text or 'priority queue' in text:
            _, norm_ds = self.normalizer.normalize_claim('code_fact', 'data_structure', 'priority_queue', 'priority_queue')
            claims.append(Claim('code_fact', 'data_structure', norm_ds, ev.evidence_id, 0.86, 'priority_queue', 'heuristic'))
        if 'deque' in text or 'queue' in text:
            _, norm_ds = self.normalizer.normalize_claim('code_fact', 'data_structure', 'queue', 'queue')
            claims.append(Claim('code_fact', 'data_structure', norm_ds, ev.evidence_id, 0.82, 'queue', 'heuristic'))
        return claims

    def _extract_from_table(self, ev: EvidenceObject) -> List[Claim]:
        claims: List[Claim] = []
        numeric_metrics = ev.structured_content.get('numeric_metrics', {})
        for metric, value in numeric_metrics.items():
            normalized_metric = self.normalizer.normalize_metric_name(str(metric).lower())
            if normalized_metric in _METRIC_NAMES:
                normalized_value = self.normalizer.normalize_numeric_value(float(value), raw_text=f'{metric}={value}').value
                claims.append(Claim('metric_fact', normalized_metric, normalized_value, ev.evidence_id, 0.93, f'{metric}={value}', 'heuristic'))
        return claims

    def _extract_from_diagram(self, ev: EvidenceObject) -> List[Claim]:
        claims: List[Claim] = []
        components = {str(x).lower() for x in ev.structured_content.get('detected_components', [])}
        labels = {str(x).lower() for x in ev.structured_content.get('detected_labels', [])}
        if ({'op_amp', 'feedback', 'feedback_loop'} & components) or ('feedback_loop' in labels):
            _, norm_feedback = self.normalizer.normalize_claim('diagram_fact', 'feedback_loop', 'present', 'feedback_loop')
            claims.append(Claim('diagram_fact', 'feedback_loop', norm_feedback, ev.evidence_id, 0.72, 'feedback_loop', 'heuristic'))
        return claims
