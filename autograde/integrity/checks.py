from __future__ import annotations

import ast
import io
import keyword
import re
import tokenize
from collections import Counter, defaultdict
from math import log
from dataclasses import dataclass
from difflib import SequenceMatcher
from itertools import combinations
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from autograde.models import EvidenceObject, Submission


@dataclass(slots=True)
class ExternalSource:
    source_id: str
    text: str
    metadata: Dict[str, str] | None = None


def _normalize_text(text: str) -> list[str]:
    return [tok.lower() for tok in re.findall(r"[a-zA-Z_][a-zA-Z0-9_'-]*", text)]


def _normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _paragraphs(text: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]
    if parts:
        return parts
    return [text.strip()] if text.strip() else []


def _shingles(tokens: Sequence[str], k: int = 5) -> set[str]:
    if len(tokens) < k:
        return {" ".join(tokens)} if tokens else set()
    return {" ".join(tokens[i : i + k]) for i in range(len(tokens) - k + 1)}


def _multiset_jaccard(a: Sequence[str], b: Sequence[str]) -> float:
    if not a or not b:
        return 0.0
    ca, cb = Counter(a), Counter(b)
    keys = set(ca) | set(cb)
    inter = sum(min(ca[k], cb[k]) for k in keys)
    union = sum(max(ca[k], cb[k]) for k in keys)
    return inter / union if union else 0.0


def _jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _text_similarity(a: str, b: str) -> float:
    if not a.strip() or not b.strip():
        return 0.0
    tokens_a = _normalize_text(a)
    tokens_b = _normalize_text(b)
    shingle = _jaccard(_shingles(tokens_a), _shingles(tokens_b))
    edit = SequenceMatcher(None, a[:12000], b[:12000]).ratio()
    bag = _multiset_jaccard(tokens_a, tokens_b)
    return 0.45 * shingle + 0.3 * edit + 0.25 * bag


def _safe_preview(text: str, limit: int = 180) -> str:
    text = re.sub(r"\s+", " ", text.strip())
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _severity(score: float, low: float, high: float) -> str:
    if score >= high:
        return "high"
    if score >= low:
        return "medium"
    return "low"


_COMMON_ACADEMIC_PHRASES = {
    "in this paper",
    "the results demonstrate",
    "future work",
    "shortest path",
    "weighted graph",
    "source vertex",
    "all other vertices",
    "algorithm computes",
}


_GENERIC_CODE_IDENTIFIERS = {
    "i", "j", "k", "u", "v", "x", "y", "z", "n", "m", "idx", "node", "nodes", "edge", "edges",
    "graph", "adj", "src", "start", "end", "cur", "curr", "next", "nxt", "queue", "q", "stack",
    "visited", "seen", "dist", "out", "order", "result", "res", "data", "value", "values",
    "append", "pop", "get", "add", "remove", "update", "items", "keys", "len", "range", "print",
}


_STANDARD_ALGORITHM_NAMES = {
    "bfs", "dfs", "dijkstra", "bellman_ford", "bellmanford", "astar", "kruskal", "prim",
    "toposort", "topological_sort", "binary_search", "merge_sort", "quick_sort", "heapsort",
}


def _raw_code_identifiers(code: str) -> set[str]:
    names: set[str] = set()
    try:
        tree = ast.parse(code or "")
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                names.add(node.id.lower())
            elif isinstance(node, ast.FunctionDef):
                names.add(node.name.lower())
            elif isinstance(node, ast.Attribute):
                names.add(node.attr.lower())
    except Exception:
        for tok in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", code or ""):
            names.add(tok.lower())
    return {n for n in names if len(n) > 2 and n not in _GENERIC_CODE_IDENTIFIERS and not keyword.iskeyword(n)}


def _shared_distinctive_identifiers(code_a: str, code_b: str) -> set[str]:
    return _raw_code_identifiers(code_a) & _raw_code_identifiers(code_b)


def _contains_citation_context(text: str) -> bool:
    hay = text.lower()
    patterns = [
        r"\[[0-9]{1,3}(?:\s*,\s*[0-9]{1,3})*\]",
        r"\([A-Z][A-Za-z'`.-]+,?\s*(?:19|20)\d{2}\)",
        r"according to\s+[A-Z][A-Za-z'`.-]+",
        r"et al\.",
        r"references?",
        r"bibliograph",
        r'"[^"]{20,}"',
    ]
    return any(re.search(p, text) for p in patterns)


def _token_overlap_count(a: Sequence[str], b: Sequence[str]) -> int:
    if not a or not b:
        return 0
    ca, cb = Counter(a), Counter(b)
    return sum(min(ca[k], cb[k]) for k in set(ca) & set(cb))


def _rare_token_ratio(tokens: Sequence[str], global_df: Counter[str]) -> float:
    if not tokens:
        return 0.0
    unique = set(tokens)
    rare = [t for t in unique if global_df.get(t, 0) <= 2 and len(t) > 4 and t not in _COMMON_ACADEMIC_PHRASES]
    return len(rare) / max(1, len(unique))


def _is_boilerplate_text_pair(a: str, b: str, global_df: Counter[str] | None = None) -> bool:
    ta = _normalize_text(a)
    tb = _normalize_text(b)
    overlap = _token_overlap_count(ta, tb)
    if overlap < 10:
        return True
    shared = set(ta) & set(tb)
    if shared and len(shared) <= 6 and all(tok in _COMMON_ACADEMIC_PHRASES or len(tok) <= 4 for tok in shared):
        return True
    if global_df is not None:
        rarity = min(_rare_token_ratio(ta, global_df), _rare_token_ratio(tb, global_df))
        if overlap < 18 and rarity < 0.12:
            return True
    return False


def _code_distinctiveness(tokens: Sequence[str]) -> float:
    if not tokens:
        return 0.0
    counts = Counter(tokens)
    informative = [t for t in counts if t not in {"ID", "CONST", "ARG", "Name", "Load", "Store", "Call", "Expr", "Module", "Assign", "Return"}]
    return len(informative) / max(1, len(counts))


def _is_template_source(source: ExternalSource | None) -> bool:
    if not source:
        return False
    metadata = source.metadata or {}
    return bool(metadata.get("is_template") or metadata.get("source_type") in {"template", "starter_code", "starter_text"})


def _review_recommendation(severity: str) -> str:
    return "manual_review" if severity in {"medium", "high"} else "inspect_if_needed"


class _UnionFind:
    def __init__(self, items: Sequence[str]) -> None:
        self.parent = {x: x for x in items}

    def find(self, x: str) -> str:
        p = self.parent[x]
        if p != x:
            self.parent[x] = self.find(p)
        return self.parent[x]

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


class IntegrityEngine:
    """Explainable plagiarism and similarity checks.

    This engine is still offline-only: external matching is limited to an
    instructor-provided source corpus. The design focuses on traceable flags,
    matched spans, severity, and confidence instead of opaque judgments.
    """

    def _build_text_df(self, texts: Sequence[str]) -> Counter[str]:
        df: Counter[str] = Counter()
        for text in texts:
            for tok in set(_normalize_text(text)):
                df[tok] += 1
        return df

    def _text_match_allowed(
        self,
        submission_text: str,
        source_text: str,
        global_df: Counter[str] | None = None,
        source: ExternalSource | None = None,
    ) -> tuple[bool, str | None]:
        toks_a = _normalize_text(submission_text)
        toks_b = _normalize_text(source_text)
        overlap = _token_overlap_count(toks_a, toks_b)
        if overlap < 12:
            return False, "short_overlap"
        if _contains_citation_context(submission_text):
            return False, "citation_context"
        if _is_template_source(source):
            return False, "template_source"
        if _is_boilerplate_text_pair(submission_text, source_text, global_df=global_df):
            return False, "boilerplate_or_common_knowledge"
        return True, None

    def _code_match_allowed(
        self,
        normalized_student: str,
        normalized_source: str,
        source: ExternalSource | None = None,
        raw_student: str = "",
        raw_source: str = "",
    ) -> tuple[bool, str | None]:
        toks_a = normalized_student.split()
        toks_b = normalized_source.split()
        overlap = _token_overlap_count(toks_a, toks_b)
        if overlap < 18:
            return False, "short_code_overlap"
        if _is_template_source(source):
            return False, "template_source"
        shared_ids = _shared_distinctive_identifiers(raw_student, raw_source) if (raw_student and raw_source) else set()
        nonstandard_shared = {s for s in shared_ids if s not in _STANDARD_ALGORITHM_NAMES}
        if not nonstandard_shared:
            return False, "common_algorithm_structure"
        if len(nonstandard_shared) < 2 and overlap < 42:
            return False, "common_algorithm_structure"
        if min(_code_distinctiveness(toks_a), _code_distinctiveness(toks_b)) < 0.18 and overlap < 48:
            return False, "common_algorithm_structure"
        return True, None

    # ---------- Public API ----------

    def check_external_sources(
        self,
        submission: Submission,
        source_corpus: Sequence[ExternalSource] | None = None,
        threshold: float = 0.35,
    ) -> List[Dict[str, str]]:
        if not source_corpus:
            return []

        text_flags = self._check_external_text_similarity(submission, source_corpus, threshold=threshold)
        code_flags = self._check_external_code_similarity(submission, source_corpus, threshold=max(0.45, threshold + 0.1))
        return sorted(text_flags + code_flags, key=lambda x: float(x.get("similarity", 0.0)), reverse=True)

    def check_intra_cohort_similarity(
        self,
        submissions: List[Submission],
        text_threshold: float = 0.55,
        code_threshold: float = 0.75,
    ) -> List[Dict[str, str]]:
        pair_flags: List[Dict[str, str]] = []
        suspicious_edges: list[Tuple[str, str]] = []

        for sub_a, sub_b in combinations(submissions, 2):
            text_report = self._pairwise_text_overlap(sub_a, sub_b)
            code_report = self._pairwise_code_overlap(sub_a, sub_b)

            max_text = text_report.get("similarity", 0.0)
            max_code = code_report.get("similarity", 0.0)
            if max_text >= text_threshold or max_code >= code_threshold:
                suspicious_edges.append((sub_a.submission_id, sub_b.submission_id))
                severity = _severity(max(max_text, max_code), low=min(text_threshold, code_threshold), high=max(text_threshold + 0.2, code_threshold + 0.1))
                pair_flags.append(
                    {
                        "type": "intra_cohort_similarity",
                        "submission_a": sub_a.submission_id,
                        "submission_b": sub_b.submission_id,
                        "text_similarity": f"{max_text:.3f}",
                        "code_similarity": f"{max_code:.3f}",
                        "severity": severity,
                        "confidence": f"{max(max_text, max_code):.3f}",
                        "matched_text_evidence_a": text_report.get("evidence_a", ""),
                        "matched_text_evidence_b": text_report.get("evidence_b", ""),
                        "matched_code_evidence_a": code_report.get("evidence_a", ""),
                        "matched_code_evidence_b": code_report.get("evidence_b", ""),
                        "text_preview_a": text_report.get("preview_a", ""),
                        "text_preview_b": text_report.get("preview_b", ""),
                        "code_preview_a": code_report.get("preview_a", ""),
                        "code_preview_b": code_report.get("preview_b", ""),
                        "review_recommendation": _review_recommendation(severity),
                    }
                )

        pair_flags.extend(self._cohort_cluster_flags(submissions, suspicious_edges))
        return pair_flags

    # ---------- External text plagiarism ----------

    def _check_external_text_similarity(
        self,
        submission: Submission,
        source_corpus: Sequence[ExternalSource],
        threshold: float,
    ) -> List[Dict[str, str]]:
        flags: List[Dict[str, str]] = []
        text_evidence = [e for e in submission.evidence if e.modality == "text" and e.content]
        if not text_evidence:
            return []
        corpus_texts = [e.content or "" for e in text_evidence] + [s.text for s in source_corpus]
        global_df = self._build_text_df(corpus_texts)

        for evidence in text_evidence:
            paragraphs = _paragraphs(evidence.content or "")
            for idx, para in enumerate(paragraphs, start=1):
                if len(_normalize_text(para)) < 12:
                    continue
                best = None
                for source in source_corpus:
                    src_chunks = _paragraphs(source.text)
                    for source_idx, chunk in enumerate(src_chunks, start=1):
                        allowed, reason = self._text_match_allowed(para, chunk, global_df=global_df, source=source)
                        if not allowed:
                            continue
                        sim = _text_similarity(para, chunk)
                        if best is None or sim > best[0]:
                            best = (sim, source, chunk, source_idx, reason)
                if best and best[0] >= threshold:
                    sim, source, source_chunk, source_idx, _ = best
                    severity = _severity(sim, threshold, min(0.8, threshold + 0.25))
                    flags.append(
                        {
                            "type": "external_text_similarity",
                            "source_id": source.source_id,
                            "submission_id": submission.submission_id,
                            "evidence_id": evidence.evidence_id,
                            "paragraph_index": str(idx),
                            "source_chunk_index": str(source_idx),
                            "similarity": f"{sim:.3f}",
                            "severity": severity,
                            "confidence": f"{sim:.3f}",
                            "matched_span_preview": _safe_preview(para),
                            "source_span_preview": _safe_preview(source_chunk),
                            "message": "Submission text is substantially similar to a configured external source segment after citation/template/common-knowledge filtering.",
                            "review_recommendation": _review_recommendation(severity),
                        }
                    )
        return flags

    # ---------- External code plagiarism ----------

    def _check_external_code_similarity(
        self,
        submission: Submission,
        source_corpus: Sequence[ExternalSource],
        threshold: float,
    ) -> List[Dict[str, str]]:
        flags: List[Dict[str, str]] = []
        code_evidence = [e for e in submission.evidence if e.modality == "code" and e.content]
        if not code_evidence:
            return []

        normalized_sources: list[tuple[ExternalSource, str]] = []
        for source in source_corpus:
            normalized_sources.append((source, self._normalize_code(source.text)))

        for evidence in code_evidence:
            normalized_student = self._normalize_code(evidence.content or "")
            if not normalized_student.strip():
                continue
            best = None
            for source, normalized_source in normalized_sources:
                allowed, reason = self._code_match_allowed(normalized_student, normalized_source, source=source, raw_student=evidence.content or "", raw_source=source.text)
                if not allowed:
                    continue
                sim = self._code_similarity_from_normalized(normalized_student, normalized_source)
                if best is None or sim > best[0]:
                    best = (sim, source, normalized_source, reason)
            if best and best[0] >= threshold:
                sim, source, normalized_source, _ = best
                severity = _severity(sim, threshold, min(0.93, threshold + 0.2))
                flags.append(
                    {
                        "type": "external_code_similarity",
                        "source_id": source.source_id,
                        "submission_id": submission.submission_id,
                        "evidence_id": evidence.evidence_id,
                        "similarity": f"{sim:.3f}",
                        "severity": severity,
                        "confidence": f"{sim:.3f}",
                        "matched_span_preview": _safe_preview(evidence.content or ""),
                        "source_span_preview": _safe_preview(source.text),
                        "message": "Submission code is substantially similar to external code after starter-code/common-structure filtering.",
                        "review_recommendation": _review_recommendation(severity),
                    }
                )
        return flags

    # ---------- Intra-cohort analysis ----------

    def _pairwise_text_overlap(self, sub_a: Submission, sub_b: Submission) -> Dict[str, object]:
        text_a = [e for e in sub_a.evidence if e.modality == "text" and e.content]
        text_b = [e for e in sub_b.evidence if e.modality == "text" and e.content]
        corpus_texts = [e.content or "" for e in text_a + text_b]
        global_df = self._build_text_df(corpus_texts)
        best: Dict[str, object] = {"similarity": 0.0}
        for ea in text_a:
            for eb in text_b:
                allowed, _ = self._text_match_allowed(ea.content or "", eb.content or "", global_df=global_df, source=None)
                if not allowed:
                    continue
                sim = _text_similarity(ea.content or "", eb.content or "")
                if sim > float(best["similarity"]):
                    best = {
                        "similarity": sim,
                        "evidence_a": ea.evidence_id,
                        "evidence_b": eb.evidence_id,
                        "preview_a": _safe_preview(ea.content or ""),
                        "preview_b": _safe_preview(eb.content or ""),
                    }
        return best

    def _pairwise_code_overlap(self, sub_a: Submission, sub_b: Submission) -> Dict[str, object]:
        code_a = [e for e in sub_a.evidence if e.modality == "code" and e.content]
        code_b = [e for e in sub_b.evidence if e.modality == "code" and e.content]
        best: Dict[str, object] = {"similarity": 0.0}
        for ea in code_a:
            norm_a = self._normalize_code(ea.content or "")
            if not norm_a.strip():
                continue
            for eb in code_b:
                norm_b = self._normalize_code(eb.content or "")
                if not norm_b.strip():
                    continue
                allowed, _ = self._code_match_allowed(norm_a, norm_b, source=None, raw_student=ea.content or "", raw_source=eb.content or "")
                if not allowed:
                    continue
                sim = self._code_similarity_from_normalized(norm_a, norm_b)
                if sim > float(best["similarity"]):
                    best = {
                        "similarity": sim,
                        "evidence_a": ea.evidence_id,
                        "evidence_b": eb.evidence_id,
                        "preview_a": _safe_preview(ea.content or ""),
                        "preview_b": _safe_preview(eb.content or ""),
                    }
        return best

    def _cohort_cluster_flags(self, submissions: List[Submission], edges: list[Tuple[str, str]]) -> List[Dict[str, str]]:
        if not edges:
            return []
        uf = _UnionFind([s.submission_id for s in submissions])
        for a, b in edges:
            uf.union(a, b)
        clusters: dict[str, list[str]] = defaultdict(list)
        for s in submissions:
            clusters[uf.find(s.submission_id)].append(s.submission_id)
        flags: list[Dict[str, str]] = []
        for members in clusters.values():
            if len(members) >= 3:
                flags.append(
                    {
                        "type": "intra_cohort_cluster",
                        "members": ",".join(sorted(members)),
                        "severity": "high",
                        "confidence": f"{min(0.99, 0.65 + 0.1 * len(members)):.3f}",
                        "message": "A cluster of mutually similar submissions was detected in the cohort.",
                        "review_recommendation": "manual_review",
                    }
                )
        return flags

    # ---------- Code normalization ----------

    def _normalize_code(self, code: str) -> str:
        code = code or ""
        try:
            tree = ast.parse(code)
            return self._normalize_code_ast(tree)
        except Exception:
            return self._normalize_code_tokens(code)

    def _normalize_code_ast(self, tree: ast.AST) -> str:
        parts: list[str] = []
        for node in ast.walk(tree):
            node_type = type(node).__name__
            if isinstance(node, ast.Name):
                parts.append("ID")
            elif isinstance(node, ast.Constant):
                parts.append("CONST")
            elif isinstance(node, ast.Attribute):
                parts.append("ATTR")
            elif isinstance(node, ast.arg):
                parts.append("ARG")
            elif isinstance(node, ast.FunctionDef):
                parts.extend(["FUNC", str(len(node.args.args))])
            elif isinstance(node, ast.Call):
                parts.append("CALL")
            else:
                parts.append(node_type)
        return " ".join(parts)

    def _normalize_code_tokens(self, code: str) -> str:
        out: list[str] = []
        try:
            for tok in tokenize.generate_tokens(io.StringIO(code).readline):
                if tok.type == tokenize.NAME:
                    if tok.string in keyword.kwlist:
                        out.append(tok.string)
                    else:
                        out.append("ID")
                elif tok.type == tokenize.NUMBER:
                    out.append("NUM")
                elif tok.type == tokenize.STRING:
                    out.append("STR")
                elif tok.type == tokenize.OP:
                    out.append(tok.string)
        except Exception:
            return _normalize_ws(code)
        return " ".join(out)

    @staticmethod
    def _code_similarity_from_normalized(a: str, b: str) -> float:
        if not a.strip() or not b.strip():
            return 0.0
        tokens_a = a.split()
        tokens_b = b.split()
        bag = _multiset_jaccard(tokens_a, tokens_b)
        edit = SequenceMatcher(None, a[:12000], b[:12000]).ratio()
        return 0.6 * bag + 0.4 * edit
