from __future__ import annotations

import re
from collections import Counter
from statistics import mean
from typing import Iterable, Sequence

from autograde.evaluators.base import BaseEvaluator
from autograde.models import EvidenceObject, EvaluatorResult
from autograde.rubric import Criterion


def _safe_div(a: float, b: float) -> float:
    return a / b if b else 0.0


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _text_items(evidence: Sequence[EvidenceObject]) -> list[EvidenceObject]:
    return [e for e in evidence if e.modality == "text" and e.content]


def _code_items(evidence: Sequence[EvidenceObject]) -> list[EvidenceObject]:
    return [e for e in evidence if e.modality == "code" and e.content]


def _execution_items(evidence: Sequence[EvidenceObject]) -> list[EvidenceObject]:
    return [e for e in evidence if e.modality == "execution"]


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z_][a-zA-Z0-9_'-]*", text.lower())


def _top_keywords(items: Iterable[str], stopwords: set[str], top_k: int = 12) -> set[str]:
    counter = Counter(tok for text in items for tok in _tokenize(text) if tok not in stopwords and len(tok) > 2)
    return {token for token, _ in counter.most_common(top_k)}


class RequirementsCoverageEvaluator(BaseEvaluator):
    evaluator_id = "requirements_coverage"

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        required_modalities = set(criterion.required_modalities)
        present_modalities = {e.modality for e in evidence}
        coverage = _safe_div(len(required_modalities & present_modalities), len(required_modalities)) if required_modalities else 1.0
        score = round(criterion.max_score * coverage, 2)
        rationale = (
            f"Coverage matched {len(required_modalities & present_modalities)} of {len(required_modalities)} required modalities."
            if required_modalities
            else "No required modalities were specified; evidence presence was treated as full coverage."
        )
        return EvaluatorResult(
            evaluator_id=self.evaluator_id,
            criterion_id=criterion.criterion_id,
            score=score,
            max_score=criterion.max_score,
            confidence=0.96 if evidence else 0.9,
            rationale=rationale,
            supporting_evidence=[e.evidence_id for e in evidence[:5]],
        )


class TextQualityEvaluator(BaseEvaluator):
    evaluator_id = "text_quality"

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        texts = _text_items(evidence)
        if not texts:
            return EvaluatorResult(
                evaluator_id=self.evaluator_id,
                criterion_id=criterion.criterion_id,
                score=0.0,
                max_score=criterion.max_score,
                confidence=0.85,
                rationale="No text evidence found for text-quality evaluation.",
            )
        contents = [t.content or "" for t in texts]
        word_counts = [len(_tokenize(c)) for c in contents]
        sentence_counts = [max(1, len(re.findall(r"[.!?]", c))) for c in contents]
        avg_words = mean(word_counts) if word_counts else 0.0
        avg_sentence_len = mean(w / s for w, s in zip(word_counts, sentence_counts)) if sentence_counts else 0.0
        headings = sum(1 for c in contents if c.strip().startswith(("#", "Title:", "Abstract", "Conclusion", "Method")))
        lexical_diversity = _safe_div(len(set(tok for c in contents for tok in _tokenize(c))), sum(word_counts))

        coverage_score = _clamp01(avg_words / 90.0)
        structure_score = _clamp01(headings / max(1, len(texts) // 3 + 1))
        readability_score = 1.0 - _clamp01(abs(avg_sentence_len - 20.0) / 20.0)
        diversity_score = _clamp01(lexical_diversity / 0.55)
        normalized = 0.35 * coverage_score + 0.2 * structure_score + 0.25 * readability_score + 0.2 * diversity_score
        score = round(normalized * criterion.max_score, 2)
        rationale = (
            "Text-quality score used content coverage, basic structural markers, sentence-length balance, and lexical diversity heuristics."
        )
        return EvaluatorResult(
            evaluator_id=self.evaluator_id,
            criterion_id=criterion.criterion_id,
            score=score,
            max_score=criterion.max_score,
            confidence=0.78,
            rationale=rationale,
            supporting_evidence=[e.evidence_id for e in texts[:5]],
        )


class ArgumentationEvaluator(BaseEvaluator):
    evaluator_id = "argumentation"

    _claim_markers = {"therefore", "thus", "hence", "however", "because", "although", "since", "conclude", "shows"}
    _evidence_markers = {"for example", "evidence", "result", "observed", "measured", "found", "according"}

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        texts = _text_items(evidence)
        if not texts:
            return EvaluatorResult(
                evaluator_id=self.evaluator_id,
                criterion_id=criterion.criterion_id,
                score=0.0,
                max_score=criterion.max_score,
                confidence=0.8,
                rationale="No textual argument found.",
            )
        joined = " ".join(t.content.lower() for t in texts[:12])
        claim_hits = sum(1 for token in self._claim_markers if token in joined)
        evidence_hits = sum(1 for token in self._evidence_markers if token in joined)
        contrast_score = 1.0 if any(word in joined for word in ["however", "although", "but"]) else 0.0
        normalized = 0.45 * _clamp01(claim_hits / 5.0) + 0.35 * _clamp01(evidence_hits / 4.0) + 0.2 * contrast_score
        score = round(normalized * criterion.max_score, 2)
        return EvaluatorResult(
            evaluator_id=self.evaluator_id,
            criterion_id=criterion.criterion_id,
            score=score,
            max_score=criterion.max_score,
            confidence=0.74,
            rationale="Argumentation score used claim markers, evidence markers, and presence of contrast/qualification language.",
            supporting_evidence=[e.evidence_id for e in texts[:5]],
        )


class CodeQualityEvaluator(BaseEvaluator):
    evaluator_id = "code_quality"

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        code_items = _code_items(evidence)
        if not code_items:
            return EvaluatorResult(
                evaluator_id=self.evaluator_id,
                criterion_id=criterion.criterion_id,
                score=0.0,
                max_score=criterion.max_score,
                confidence=0.9,
                rationale="No code evidence found.",
            )
        file_items = [e for e in code_items if e.subtype == "file"]
        function_items = [e for e in code_items if e.subtype == "function"]
        function_count = sum(int(item.structured_content.get("function_count", 0)) for item in file_items) or len(function_items)
        docstring_count = sum(1 for item in function_items if item.structured_content.get("has_docstring"))
        line_counts = [int(item.structured_content.get("line_count", 0)) for item in function_items if item.structured_content.get("line_count")]
        comment_line_count = sum(int(item.structured_content.get("comment_line_count", 0)) for item in file_items)
        parse_error = any(bool(item.structured_content.get("parse_error")) for item in file_items)

        structure_score = _clamp01(function_count / 3.0)
        documentation_score = _clamp01((docstring_count + min(comment_line_count, 4)) / max(1, function_count + 2))
        function_length_score = 1.0 - _clamp01(abs((mean(line_counts) if line_counts else 12.0) - 18.0) / 25.0)
        normalized = 0.45 * structure_score + 0.3 * documentation_score + 0.25 * function_length_score
        if parse_error:
            normalized *= 0.55
        score = round(normalized * criterion.max_score, 2)
        rationale = "Code-quality score used parsed structure, documentation signals, and function-size balance heuristics."
        return EvaluatorResult(
            evaluator_id=self.evaluator_id,
            criterion_id=criterion.criterion_id,
            score=score,
            max_score=criterion.max_score,
            confidence=0.8 if not parse_error else 0.58,
            rationale=rationale,
            supporting_evidence=[e.evidence_id for e in code_items[:5]],
            flags=[{"type": "parse_error"}] if parse_error else [],
        )


class DiagramCompletenessEvaluator(BaseEvaluator):
    evaluator_id = "diagram_completeness"

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        diagrams = [e for e in evidence if e.modality in {"diagram", "image"}]
        if not diagrams:
            return EvaluatorResult(
                evaluator_id=self.evaluator_id,
                criterion_id=criterion.criterion_id,
                score=0.0,
                max_score=criterion.max_score,
                confidence=0.9,
                rationale="No diagram evidence detected.",
            )
        label_count = sum(len(e.structured_content.get("detected_labels", [])) for e in diagrams)
        component_count = sum(len(e.structured_content.get("detected_components", [])) for e in diagrams)
        normalized = 0.5 * _clamp01(component_count / 4.0) + 0.5 * _clamp01(label_count / 4.0)
        return EvaluatorResult(
            evaluator_id=self.evaluator_id,
            criterion_id=criterion.criterion_id,
            score=round(normalized * criterion.max_score, 2),
            max_score=criterion.max_score,
            confidence=0.72,
            rationale="Diagram-completeness score used detected components and labels.",
            supporting_evidence=[e.evidence_id for e in diagrams[:5]],
        )


class TechnicalCorrectnessEvaluator(BaseEvaluator):
    evaluator_id = "technical_correctness"

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        required = set(criterion.required_modalities)
        relevant = [e for e in evidence if e.modality in required] if required else list(evidence)
        if not relevant:
            return EvaluatorResult(
                evaluator_id=self.evaluator_id,
                criterion_id=criterion.criterion_id,
                score=0.0,
                max_score=criterion.max_score,
                confidence=0.9,
                rationale="No relevant evidence was available for technical-correctness checks.",
            )
        code_items = [e for e in relevant if e.modality == "code"]
        text_items = [e for e in relevant if e.modality == "text"]
        signal = 0.0
        if code_items:
            file_metrics = [e.structured_content for e in code_items if e.subtype == "file"]
            functions = sum(int(m.get("function_count", 0)) for m in file_metrics)
            loops = sum(int(m.get("loop_count", 0)) for m in file_metrics)
            parse_errors = sum(1 for m in file_metrics if m.get("parse_error"))
            signal += 0.45 * _clamp01(functions / 2.0)
            signal += 0.25 * _clamp01(loops / 1.0)
            signal -= 0.3 * _clamp01(parse_errors)
        if text_items:
            joined = " ".join((e.content or "").lower() for e in text_items[:10])
            concept_markers = sum(1 for token in ["algorithm", "method", "complexity", "correct", "result", "experiment"] if token in joined)
            signal += 0.3 * _clamp01(concept_markers / 4.0)
        score = round(_clamp01(signal) * criterion.max_score, 2)
        return EvaluatorResult(
            evaluator_id=self.evaluator_id,
            criterion_id=criterion.criterion_id,
            score=score,
            max_score=criterion.max_score,
            confidence=0.7,
            rationale="Technical-correctness score used parsed code signals and discipline-neutral technical markers in text.",
            supporting_evidence=[e.evidence_id for e in relevant[:5]],
        )


class CrossModalConsistencyEvaluator(BaseEvaluator):
    evaluator_id = "cross_modal_consistency"

    _stopwords = {
        "the", "and", "for", "with", "that", "this", "from", "into", "are", "was", "were", "use", "uses",
        "code", "report", "method", "results", "algorithm", "data", "graph", "function", "tested", "well",
    }

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        modalities = {e.modality for e in evidence}
        required = set(criterion.required_modalities)
        if not required.issubset(modalities):
            return EvaluatorResult(
                evaluator_id=self.evaluator_id,
                criterion_id=criterion.criterion_id,
                score=round(0.35 * criterion.max_score, 2),
                max_score=criterion.max_score,
                confidence=0.7,
                rationale="Some required modalities were missing, so cross-modal consistency could only be partially assessed.",
                supporting_evidence=[e.evidence_id for e in evidence[:5]],
                flags=[{"type": "missing_modality", "required": sorted(required - modalities)}],
            )
        text_keywords = _top_keywords((e.content or "" for e in evidence if e.modality == "text"), self._stopwords)
        code_keywords = set()
        for item in evidence:
            if item.modality != "code":
                continue
            if item.subtype == "function":
                name = str(item.structured_content.get("function_name", "")).lower()
                if name:
                    code_keywords.add(name)
            code_keywords.update(tok for tok in _tokenize(item.content or "") if tok not in self._stopwords and len(tok) > 2)
        overlap = text_keywords & code_keywords
        overlap_score = _clamp01(len(overlap) / max(2, min(len(text_keywords) or 1, 6)))
        modality_score = 1.0 if required.issubset(modalities) else 0.0
        normalized = 0.5 * modality_score + 0.5 * overlap_score
        rationale = (
            f"Cross-modal consistency used modality coverage and keyword overlap; overlapping terms included: {', '.join(sorted(list(overlap))[:5]) or 'none'}"
        )
        return EvaluatorResult(
            evaluator_id=self.evaluator_id,
            criterion_id=criterion.criterion_id,
            score=round(normalized * criterion.max_score, 2),
            max_score=criterion.max_score,
            confidence=0.77,
            rationale=rationale,
            supporting_evidence=[e.evidence_id for e in evidence[:6]],
        )



class DesignFunctionalPlausibilityEvaluator(BaseEvaluator):
    evaluator_id = "design_functional_plausibility"

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        diagrams = [e for e in evidence if e.modality == "diagram"]
        tables = [e for e in evidence if e.modality == "table"]
        if not diagrams:
            return EvaluatorResult(
                evaluator_id=self.evaluator_id,
                criterion_id=criterion.criterion_id,
                score=0.0,
                max_score=criterion.max_score,
                confidence=0.84,
                rationale="No diagram evidence was available for functional-plausibility checks.",
            )
        metadata = criterion.metadata or {}
        accepted_families = set(metadata.get("accepted_families", []))
        required_components = set(metadata.get("required_components", []))
        diagram = diagrams[0]
        components = set(diagram.structured_content.get("detected_components", []))
        family = str(diagram.structured_content.get("diagram_family", "unknown"))
        family_score = 1.0 if family in accepted_families else (0.6 if family != "unknown" else 0.35)
        component_score = _safe_div(len(required_components & components), len(required_components)) if required_components else 0.7
        sim_signal = 0.0
        for table in tables:
            metrics = table.structured_content.get("metrics", {})
            if any(k in metrics for k in ["gain", "bandwidth", "cutoff", "stability", "phase_margin"]):
                sim_signal = 1.0
                break
        plausibility = float(diagram.structured_content.get("functional_plausibility", 0.0))
        normalized = 0.45 * family_score + 0.35 * component_score + 0.1 * plausibility + 0.1 * sim_signal
        flags = []
        if family == "unknown" and component_score >= 0.6:
            flags.append({"type": "plausible_unknown_design_family"})
        return EvaluatorResult(
            evaluator_id=self.evaluator_id,
            criterion_id=criterion.criterion_id,
            score=round(_clamp01(normalized) * criterion.max_score, 2),
            max_score=criterion.max_score,
            confidence=0.73 if family != "unknown" else 0.62,
            rationale=(
                "Design plausibility used detected circuit-family cues, required component coverage, and any available simulation-table signals. "
                f"Detected family={family}; components={', '.join(sorted(list(components))[:6]) or 'none'}."
            ),
            supporting_evidence=[e.evidence_id for e in (diagrams[:2] + tables[:2])],
            flags=flags,
        )


class SimulationEvidenceEvaluator(BaseEvaluator):
    evaluator_id = "simulation_evidence"

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        tables = [e for e in evidence if e.modality == "table"]
        texts = _text_items(evidence)
        if not tables:
            return EvaluatorResult(
                evaluator_id=self.evaluator_id,
                criterion_id=criterion.criterion_id,
                score=0.0,
                max_score=criterion.max_score,
                confidence=0.86,
                rationale="No tabular or simulation evidence was available.",
                flags=[{"type": "missing_simulation_evidence"}],
            )
        metric_names = set()
        metric_score = 0.0
        for table in tables:
            metrics = table.structured_content.get("metrics", {})
            metric_names.update(metrics.keys())
            metric_score = max(metric_score, _clamp01(len(metrics) / 2.0))
        joined = " ".join((e.content or "").lower() for e in texts[:8])
        report_alignment = 1.0 if any(name in joined for name in metric_names) else (0.55 if metric_names else 0.0)
        normalized = 0.65 * metric_score + 0.35 * report_alignment
        return EvaluatorResult(
            evaluator_id=self.evaluator_id,
            criterion_id=criterion.criterion_id,
            score=round(_clamp01(normalized) * criterion.max_score, 2),
            max_score=criterion.max_score,
            confidence=0.78,
            rationale=(
                "Simulation evidence used extracted numeric metrics from tables/CSVs and checked whether the report referenced those metrics. "
                f"Metrics found: {', '.join(sorted(metric_names)[:5]) or 'none'}."
            ),
            supporting_evidence=[e.evidence_id for e in (tables[:3] + texts[:2])],
        )




class SubjectiveAnswerQualityEvaluator(BaseEvaluator):
    evaluator_id = "subjective_answer_quality"

    _reasoning_markers = {"because", "therefore", "however", "although", "for example", "for instance", "thus", "while", "whereas", "suggests"}
    _support_markers = {"according", "evidence", "text", "passage", "author", "quote", "quotes", "cites", "argues"}

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        texts = _text_items(evidence)
        if not texts:
            return EvaluatorResult(
                evaluator_id=self.evaluator_id,
                criterion_id=criterion.criterion_id,
                score=0.0,
                max_score=criterion.max_score,
                confidence=0.84,
                rationale="No text evidence found for subjective-answer evaluation.",
            )

        metadata = criterion.metadata or {}
        band = metadata.get("length_band", "medium")
        contents = [t.content or "" for t in texts]
        joined = "\n".join(contents).lower()
        total_words = sum(len(_tokenize(c)) for c in contents)

        band_targets = {
            "short": (20, 120),
            "medium": (80, 320),
            "long": (250, 1200),
        }
        min_words, max_words = band_targets.get(band, band_targets["medium"])
        if total_words < min_words:
            length_score = _clamp01(total_words / max(1.0, float(min_words)))
        elif total_words > max_words:
            length_score = max(0.65, 1.0 - _clamp01((total_words - max_words) / max(max_words, 1.0)))
        else:
            length_score = 1.0

        expected_concepts = metadata.get("expected_concepts", [])
        concept_hits = 0
        required_concepts = 0
        concept_details: list[str] = []
        for concept in expected_concepts:
            name = str(concept.get("name", "concept"))
            synonyms = [str(s).lower() for s in concept.get("synonyms", [])]
            required = bool(concept.get("required", True))
            required_concepts += 1 if required else 0
            pool = {name.lower(), *synonyms}
            if any(token in joined for token in pool):
                concept_hits += 1
                concept_details.append(f"covered:{name}")
            elif required:
                concept_details.append(f"missing:{name}")

        if expected_concepts:
            concept_score = _safe_div(concept_hits, max(1, len(expected_concepts)))
        else:
            # fallback: use lexical coverage and basic topicality heuristics when no concepts are specified
            keyword_score = _clamp01(len(_top_keywords(contents, {"the", "and", "for", "with", "that", "this", "from", "have", "into", "their"}, top_k=8)) / 6.0)
            concept_score = 0.75 * keyword_score + 0.25

        reasoning_hits = sum(1 for marker in self._reasoning_markers if marker in joined)
        support_hits = sum(1 for marker in self._support_markers if marker in joined)
        structure_hits = sum(1 for c in contents if c.strip().startswith(("Title:", "Introduction", "Conclusion", "Argument", "Response", "Paragraph")))

        reasoning_score = _clamp01(reasoning_hits / (2.0 if band == "short" else 4.0 if band == "medium" else 6.0))
        support_score = _clamp01(support_hits / (1.0 if band == "short" else 3.0 if band == "medium" else 5.0))
        structure_score = _clamp01((structure_hits + (1 if "however" in joined or "therefore" in joined else 0)) / (1.0 if band == "short" else 2.0 if band == "medium" else 3.0))

        if band == "short":
            normalized = 0.5 * concept_score + 0.2 * length_score + 0.2 * reasoning_score + 0.1 * support_score
        elif band == "long":
            normalized = 0.35 * concept_score + 0.15 * length_score + 0.2 * reasoning_score + 0.15 * support_score + 0.15 * structure_score
        else:
            normalized = 0.4 * concept_score + 0.2 * length_score + 0.2 * reasoning_score + 0.1 * support_score + 0.1 * structure_score

        score = round(_clamp01(normalized) * criterion.max_score, 2)
        rationale_bits = [
            f"Subjective-answer heuristics used the {band} length band",
            f"word count={total_words}",
            f"concept coverage={concept_hits}/{len(expected_concepts)}" if expected_concepts else "concept coverage used fallback topicality heuristics",
            f"reasoning markers={reasoning_hits}",
            f"support markers={support_hits}",
        ]
        if concept_details:
            rationale_bits.append("; ".join(concept_details[:6]))

        flags = []
        if expected_concepts and required_concepts and concept_hits < required_concepts:
            flags.append({"type": "missing_expected_concepts", "missing_count": required_concepts - concept_hits})

        return EvaluatorResult(
            evaluator_id=self.evaluator_id,
            criterion_id=criterion.criterion_id,
            score=score,
            max_score=criterion.max_score,
            confidence=0.71 if expected_concepts else 0.66,
            rationale=". ".join(rationale_bits) + ".",
            supporting_evidence=[e.evidence_id for e in texts[:6]],
            flags=flags,
        )


class CitationIntegrityEvaluator(BaseEvaluator):
    evaluator_id = "citation_integrity"

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        texts = _text_items(evidence)
        if not texts:
            return EvaluatorResult(
                evaluator_id=self.evaluator_id,
                criterion_id=criterion.criterion_id,
                score=0.0,
                max_score=criterion.max_score,
                confidence=0.85,
                rationale="No text evidence found for citation checks.",
            )
        joined = "\n".join(e.content or "" for e in texts[:12])
        bracket_citations = len(re.findall(r"\[[^\]]+\]", joined))
        author_year = len(re.findall(r"\([A-Z][A-Za-z\-]+,?\s+\d{4}\)", joined))
        reference_section = 1 if re.search(r"\breferences\b|\bbibliography\b", joined, flags=re.IGNORECASE) else 0
        normalized = 0.45 * _clamp01((bracket_citations + author_year) / 4.0) + 0.55 * reference_section
        score = round(normalized * criterion.max_score, 2)
        return EvaluatorResult(
            evaluator_id=self.evaluator_id,
            criterion_id=criterion.criterion_id,
            score=score,
            max_score=criterion.max_score,
            confidence=0.72,
            rationale="Citation-integrity score used in-text citation patterns and presence of a reference-like section.",
            supporting_evidence=[e.evidence_id for e in texts[:5]],
        )


class BehavioralCorrectnessEvaluator(BaseEvaluator):
    evaluator_id = "behavioral_correctness"

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        execution_items = _execution_items(evidence)
        if not execution_items:
            return EvaluatorResult(
                evaluator_id=self.evaluator_id,
                criterion_id=criterion.criterion_id,
                score=0.0,
                max_score=criterion.max_score,
                confidence=0.85,
                rationale="No execution-probe evidence was available for behavioral correctness.",
                flags=[{"type": "missing_execution_evidence"}],
            )
        tests_run = sum(int(e.structured_content.get("tests_run", 0)) for e in execution_items)
        tests_passed = sum(int(e.structured_content.get("tests_passed", 0)) for e in execution_items)
        pass_rate = _safe_div(tests_passed, tests_run)
        recovered_units = len({str(e.structured_content.get("function_name", "")) for e in execution_items if e.structured_content.get("function_name")})
        normalized = 0.8 * pass_rate + 0.2 * _clamp01(recovered_units / 2.0)
        flags = []
        if tests_run == 0:
            flags.append({"type": "execution_probe_failed"})
        elif pass_rate < 1.0:
            flags.append({"type": "partial_probe_failure", "pass_rate": round(pass_rate, 3)})
        return EvaluatorResult(
            evaluator_id=self.evaluator_id,
            criterion_id=criterion.criterion_id,
            score=round(normalized * criterion.max_score, 2),
            max_score=criterion.max_score,
            confidence=0.9 if tests_run else 0.75,
            rationale=f"Behavioral correctness used sandboxed unit probes: passed {tests_passed} of {tests_run} test(s) across {recovered_units} recovered callable unit(s).",
            supporting_evidence=[e.evidence_id for e in execution_items[:6]],
            flags=flags,
        )


class ImplementationReportAlignmentEvaluator(BaseEvaluator):
    evaluator_id = "implementation_report_alignment"

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        texts = _text_items(evidence)
        codes = _code_items(evidence)
        executions = _execution_items(evidence)
        if not texts or not codes:
            return EvaluatorResult(
                evaluator_id=self.evaluator_id,
                criterion_id=criterion.criterion_id,
                score=0.0,
                max_score=criterion.max_score,
                confidence=0.8,
                rationale="Report-code alignment could not be assessed because either text or code evidence was missing.",
            )
        joined_text = " ".join((e.content or "").lower() for e in texts[:10])
        fn_names = {str(e.structured_content.get("function_name", "")).lower() for e in codes if e.subtype == "function"}
        fn_names = {x for x in fn_names if x}
        algo_alignment = 1.0 if any(name in joined_text for name in fn_names) else 0.35
        probe_support = 0.0
        if executions:
            tests_run = sum(int(e.structured_content.get("tests_run", 0)) for e in executions)
            tests_passed = sum(int(e.structured_content.get("tests_passed", 0)) for e in executions)
            probe_support = _safe_div(tests_passed, tests_run)
        keyword_overlap = 0.0
        text_keywords = _top_keywords((e.content or "" for e in texts), {"the", "and", "for", "with", "this", "that", "code", "report", "algorithm", "implemented", "uses"})
        code_keywords = set()
        for item in codes:
            code_keywords.update(tok for tok in _tokenize(item.content or "") if len(tok) > 2)
        if text_keywords:
            keyword_overlap = _clamp01(len(text_keywords & code_keywords) / max(1, min(len(text_keywords), 5)))
        normalized = 0.45 * algo_alignment + 0.3 * keyword_overlap + 0.25 * probe_support
        return EvaluatorResult(
            evaluator_id=self.evaluator_id,
            criterion_id=criterion.criterion_id,
            score=round(normalized * criterion.max_score, 2),
            max_score=criterion.max_score,
            confidence=0.82 if executions else 0.74,
            rationale="Implementation-report alignment used function-name agreement, text/code keyword overlap, and execution-probe support when available.",
            supporting_evidence=[e.evidence_id for e in (texts[:2] + codes[:2] + executions[:2])],
        )


class ThesisStrengthEvaluator(BaseEvaluator):
    evaluator_id = "thesis_strength"

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        texts = _text_items(evidence)
        if not texts:
            return EvaluatorResult(self.evaluator_id, criterion.criterion_id, 0.0, criterion.max_score, 0.8, "No text evidence found for thesis evaluation.")
        contents = [(t.content or "") for t in texts[:8]]
        joined = " ".join(contents)
        lowered = joined.lower()
        first_segment = lowered[:500]
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", joined) if s.strip()]
        opening_sentences = " ".join(sentences[:2]).lower()
        expected = criterion.metadata.get("expected_concepts", []) if criterion.metadata else []
        expected_hits = 0
        for concept in expected:
            names = [str(concept.get("name", ""))] + [str(s) for s in concept.get("synonyms", [])]
            if any(name and name.lower() in lowered for name in names):
                expected_hits += 1
        stance_markers = sum(1 for m in ["argue", "claim", "thesis", "contend", "suggest", "this essay", "i will show", "we show"] if m in lowered)
        reason_markers = sum(1 for m in ["because", "therefore", "however", "although", "while", "yet"] if m in lowered)
        early_position = 1.0 if any(m in opening_sentences for m in ["argue", "claim", "contend", "suggest", "position", "thesis"]) else 0.0
        specificity_tokens = _top_keywords(contents, {"the", "and", "for", "with", "that", "this", "from", "have", "are", "was"}, top_k=16)
        specificity_score = _clamp01(len([tok for tok in specificity_tokens if len(tok) >= 6]) / 6.0)
        expected_score = _clamp01(_safe_div(expected_hits, max(1, len(expected)))) if expected else 0.5
        normalized = 0.30 * _clamp01(stance_markers / 4.0) + 0.20 * _clamp01(reason_markers / 4.0) + 0.25 * early_position + 0.15 * specificity_score + 0.10 * expected_score
        confidence = 0.78 if len(contents) >= 2 else 0.68
        rationale = "Thesis-strength score used early-position detection, stance cues, specificity of opening claims, and overlap with expected interpretive concepts."
        flags = [] if early_position or stance_markers else [{"type": "weak_thesis_signal"}]
        return EvaluatorResult(self.evaluator_id, criterion.criterion_id, round(normalized * criterion.max_score, 2), criterion.max_score, confidence, rationale, [e.evidence_id for e in texts[:4]], flags)


class TextualEvidenceUsageEvaluator(BaseEvaluator):
    evaluator_id = "textual_evidence_usage"

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        texts = _text_items(evidence)
        if not texts:
            return EvaluatorResult(self.evaluator_id, criterion.criterion_id, 0.0, criterion.max_score, 0.8, "No text evidence found for evidence-usage evaluation.")
        contents = [(t.content or "") for t in texts[:8]]
        joined = " ".join(contents).lower()
        quote_marks = joined.count('"') + joined.count("'")
        citation_hits = len(re.findall(r"\[[0-9]+\]|\([A-Za-z].*?[0-9]{4}.*?\)", joined))
        source_markers = sum(1 for m in ["according to", "the author", "the text", "as shown", "as noted", "writes"] if m in joined)
        integration_markers = sum(1 for m in ["for example", "this shows", "this suggests", "therefore", "because"] if m in joined)
        citation_like_spans = sum(1 for line in contents if any(tok in line.lower() for tok in ["according to", "[", "(", "author", "text"]))
        expected = criterion.metadata.get("expected_concepts", []) if criterion.metadata else []
        expected_hits = 0
        for concept in expected:
            names = [str(concept.get("name", ""))] + [str(s) for s in concept.get("synonyms", [])]
            if any(name and name.lower() in joined for name in names):
                expected_hits += 1
        normalized = 0.30 * _clamp01(citation_hits / 2.0) + 0.20 * _clamp01(source_markers / 3.0) + 0.20 * _clamp01(integration_markers / 4.0) + 0.15 * _clamp01(citation_like_spans / 3.0) + 0.15 * (_clamp01(_safe_div(expected_hits, max(1, len(expected)))) if expected else 0.5)
        flags = []
        if citation_hits == 0 and source_markers == 0:
            flags.append({"type": "weak_source_grounding"})
        rationale = "Evidence-usage score used citation markers, source attribution language, and whether cited material is integrated into the answer rather than merely named."
        return EvaluatorResult(self.evaluator_id, criterion.criterion_id, round(normalized * criterion.max_score, 2), criterion.max_score, 0.76, rationale, [e.evidence_id for e in texts[:4]], flags)


class ProofValidityEvaluator(BaseEvaluator):
    evaluator_id = "proof_validity"

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        texts = _text_items(evidence)
        if not texts:
            return EvaluatorResult(self.evaluator_id, criterion.criterion_id, 0.0, criterion.max_score, 0.82, "No proof text found.")
        contents = [(t.content or "") for t in texts[:10]]
        joined = " ".join(contents).lower()
        assumption_markers = sum(1 for m in ["let", "assume", "suppose", "given", "consider"] if m in joined)
        implication_markers = sum(1 for m in ["then", "therefore", "hence", "thus", "implies", "it follows"] if m in joined)
        conclusion_markers = sum(1 for m in ["therefore", "thus", "so the claim follows", "proved", "qed"] if m in joined)
        definition_markers = sum(1 for m in ["by definition", "by assumption", "using", "from the theorem", "lemma"] if m in joined)
        weak_jump_markers = sum(1 for m in ["clearly", "obvious", "trivial", "immediate"] if m in joined)
        equation_lines = sum(1 for c in contents if any(sym in c for sym in ['=', '≤', '>=', '<=', '=>', '∈', '⊂']))
        normalized = 0.22 * _clamp01(assumption_markers / 2.0) + 0.25 * _clamp01(implication_markers / 4.0) + 0.18 * _clamp01(conclusion_markers / 2.0) + 0.18 * _clamp01(definition_markers / 3.0) + 0.17 * _clamp01(equation_lines / 4.0)
        normalized *= (1.0 - 0.18 * _clamp01(weak_jump_markers / 2.0))
        flags = [] if weak_jump_markers == 0 else [{"type": "possible_unjustified_jump", "count": weak_jump_markers}]
        rationale = "Proof-validity score used assumption, implication, conclusion, and justification markers, plus a penalty for unsupported jumps such as 'clearly' or 'obvious'."
        confidence = 0.74 if equation_lines or definition_markers else 0.66
        return EvaluatorResult(self.evaluator_id, criterion.criterion_id, round(normalized * criterion.max_score, 2), criterion.max_score, confidence, rationale, [e.evidence_id for e in texts[:5]], flags)


class ResultAnalysisEvaluator(BaseEvaluator):
    evaluator_id = "result_analysis"

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        texts = _text_items(evidence)
        tables = [e for e in evidence if e.modality == 'table']
        joined = " ".join((t.content or "") for t in texts[:8]).lower()
        table_metrics: set[str] = set()
        for table in tables:
            sc = table.structured_content or {}
            metrics = sc.get('metrics', {}) or {}
            table_metrics.update(str(k).lower() for k in metrics.keys())
            table_metrics.update(str(k).lower() for k in ['accuracy', 'loss', 'gain', 'cutoff', 'bandwidth', 'precision', 'recall'] if sc.get(k) is not None)
        mentioned_metrics = {m for m in table_metrics if m in joined}
        comparison_markers = sum(1 for m in ["increase", "decrease", "higher", "lower", "compared", "baseline", "trend", "improved", "worse"] if m in joined)
        explanation_markers = sum(1 for m in ["because", "suggests", "indicates", "implies", "likely", "due to"] if m in joined)
        limitation_markers = sum(1 for m in ["limitation", "error", "uncertainty", "variance"] if m in joined)
        normalized = 0.25 * _clamp01(len(mentioned_metrics) / max(1, len(table_metrics) or 1)) + 0.25 * _clamp01(comparison_markers / 4.0) + 0.25 * _clamp01(explanation_markers / 3.0) + 0.15 * (1.0 if tables else 0.0) + 0.10 * _clamp01(limitation_markers / 2.0)
        flags = [] if tables else [{"type": "missing_table_support"}]
        rationale = "Result-analysis score used overlap between discussed and observed metrics, trend/comparison language, explanatory reasoning, and whether limitations were acknowledged."
        confidence = 0.79 if tables else 0.68
        return EvaluatorResult(self.evaluator_id, criterion.criterion_id, round(normalized * criterion.max_score, 2), criterion.max_score, confidence, rationale, [e.evidence_id for e in (texts[:3] + tables[:2])], flags)


class SimulationConsistencyEvaluator(BaseEvaluator):
    evaluator_id = "simulation_consistency"

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        tables = [e for e in evidence if e.modality == 'table']
        texts = _text_items(evidence)
        if not tables and not texts:
            return EvaluatorResult(self.evaluator_id, criterion.criterion_id, 0.0, criterion.max_score, 0.82, "No simulation-related evidence found.")
        joined = " ".join((t.content or "") for t in texts[:6]).lower()
        expected_metrics = [str(x).lower() for x in (criterion.metadata or {}).get('expected_metrics', [])]
        table_metrics: set[str] = set()
        for table in tables:
            sc = table.structured_content or {}
            metrics = sc.get('metrics', {}) or {}
            table_metrics.update(str(k).lower() for k in metrics.keys())
            for key in ['gain', 'cutoff', 'bandwidth', 'phase_margin', 'stability']:
                if sc.get(key) is not None:
                    table_metrics.add(key)
        text_mentions = {m for m in table_metrics | set(expected_metrics) if m in joined}
        metric_overlap = _safe_div(len(text_mentions & (table_metrics or set(expected_metrics))), max(1, len(expected_metrics or list(table_metrics) or [1])))
        signal_terms = sum(1 for m in ['simulation', 'gain', 'cutoff', 'bandwidth', 'stable', 'response', 'phase margin', 'frequency'] if m in joined)
        normalized = 0.40 * _clamp01(len(table_metrics) / 3.0) + 0.35 * _clamp01(metric_overlap) + 0.25 * _clamp01(signal_terms / 5.0)
        flags = []
        if expected_metrics and not text_mentions:
            flags.append({'type': 'expected_metrics_not_discussed', 'expected_metrics': expected_metrics})
        rationale = "Simulation-consistency score used observed metrics, overlap between expected and discussed metrics, and explicit discussion of simulated system behavior."
        confidence = 0.8 if tables else 0.66
        return EvaluatorResult(self.evaluator_id, criterion.criterion_id, round(normalized * criterion.max_score, 2), criterion.max_score, confidence, rationale, [e.evidence_id for e in (tables[:3] + texts[:2])], flags)


class DerivationStepQualityEvaluator(BaseEvaluator):
    evaluator_id = "derivation_step_quality"

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        texts = [e for e in evidence if e.modality in {"text", "equation"}]
        if not texts:
            return EvaluatorResult(self.evaluator_id, criterion.criterion_id, 0.0, criterion.max_score, 0.8, "No derivation evidence found.")
        contents = [(t.content or "") for t in texts[:12]]
        joined = " ".join(contents).lower()
        step_markers = sum(1 for m in ["=", "therefore", "thus", "hence", "implies", "so", "by"] if m in joined)
        transform_lines = sum(1 for c in contents if c.count('=') >= 1 or '->' in c or '=>' in c)
        justification_markers = sum(1 for m in ["by", "using", "substitute", "expand", "simplify", "since"] if m in joined)
        unsupported_jumps = sum(1 for m in ["clearly", "obvious", "immediate"] if m in joined)
        normalized = 0.35 * _clamp01(step_markers / 6.0) + 0.35 * _clamp01(transform_lines / 4.0) + 0.30 * _clamp01(justification_markers / 4.0)
        normalized *= (1.0 - 0.2 * _clamp01(unsupported_jumps / 2.0))
        flags = [] if unsupported_jumps == 0 else [{"type": "possible_unjustified_derivation_jump", "count": unsupported_jumps}]
        rationale = "Derivation-step score used explicit symbolic transformations, chained equalities, and justification markers, with penalties for unsupported jumps."
        return EvaluatorResult(self.evaluator_id, criterion.criterion_id, round(normalized * criterion.max_score, 2), criterion.max_score, 0.74, rationale, [e.evidence_id for e in texts[:5]], flags)


class TheoremDefinitionUseEvaluator(BaseEvaluator):
    evaluator_id = "theorem_definition_use"

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        texts = [e for e in evidence if e.modality in {"text", "equation"}]
        if not texts:
            return EvaluatorResult(self.evaluator_id, criterion.criterion_id, 0.0, criterion.max_score, 0.8, "No theorem/definition evidence found.")
        joined = " ".join((t.content or "") for t in texts[:10]).lower()
        theorem_markers = sum(1 for m in ["theorem", "lemma", "definition", "axiom", "by definition", "by theorem", "by lemma", "property"] if m in joined)
        variable_setup = sum(1 for m in ["let", "assume", "for all", "there exists", "consider"] if m in joined)
        normalized = 0.6 * _clamp01(theorem_markers / 3.0) + 0.4 * _clamp01(variable_setup / 3.0)
        flags = [] if theorem_markers > 0 else [{"type": "weak_theorem_definition_grounding"}]
        rationale = "Theorem/definition-use score checks whether the proof explicitly grounds key steps in definitions, lemmas, or setup assumptions."
        return EvaluatorResult(self.evaluator_id, criterion.criterion_id, round(normalized * criterion.max_score, 2), criterion.max_score, 0.73, rationale, [e.evidence_id for e in texts[:5]], flags)


class ConclusionTargetAlignmentEvaluator(BaseEvaluator):
    evaluator_id = "conclusion_target_alignment"

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        texts = [e for e in evidence if e.modality in {"text", "equation"}]
        if not texts:
            return EvaluatorResult(self.evaluator_id, criterion.criterion_id, 0.0, criterion.max_score, 0.8, "No conclusion-alignment evidence found.")
        contents = [(t.content or "") for t in texts[:10]]
        joined = " ".join(contents).lower()
        opening = " ".join(contents[:2]).lower()
        closing = " ".join(contents[-2:]).lower()
        goal_terms = {tok for tok in re.findall(r"[A-Za-z]{4,}", opening) if tok.lower() not in {"proof", "submission", "title", "therefore", "hence", "since", "because"}}
        closing_hits = len([tok for tok in goal_terms if tok.lower() in closing])
        conclusion_markers = sum(1 for m in ["therefore", "hence", "thus", "proved", "qed", "we conclude"] if m in closing)
        normalized = 0.55 * _clamp01(_safe_div(closing_hits, max(1, len(goal_terms)))) + 0.45 * _clamp01(conclusion_markers / 2.0)
        rationale = "Conclusion-target alignment checks whether the final portion of the solution actually returns to the initial goal rather than ending mid-argument."
        return EvaluatorResult(self.evaluator_id, criterion.criterion_id, round(normalized * criterion.max_score, 2), criterion.max_score, 0.72, rationale, [e.evidence_id for e in texts[:5]], [])


class PromptRelevanceEvaluator(BaseEvaluator):
    evaluator_id = "prompt_relevance"

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        texts = _text_items(evidence)
        if not texts:
            return EvaluatorResult(self.evaluator_id, criterion.criterion_id, 0.0, criterion.max_score, 0.82, "No text evidence found for prompt-relevance evaluation.")
        contents = [(t.content or "") for t in texts[:8]]
        joined = " ".join(contents).lower()
        metadata = criterion.metadata or {}
        expected = metadata.get("expected_concepts", [])
        prompt_terms = [str(x).lower() for x in metadata.get("prompt_terms", [])]
        required_hits = 0
        required_total = 0
        optional_hits = 0
        optional_total = 0
        for concept in expected:
            names = [str(concept.get("name", ""))] + [str(s) for s in concept.get("synonyms", [])]
            hit = any(name and name.lower() in joined for name in names)
            if concept.get("required", True):
                required_total += 1
                required_hits += 1 if hit else 0
            else:
                optional_total += 1
                optional_hits += 1 if hit else 0
        prompt_hit_count = sum(1 for tok in prompt_terms if tok and tok in joined)
        req_score = _safe_div(required_hits, max(1, required_total)) if required_total else 0.6
        opt_score = _safe_div(optional_hits, max(1, optional_total)) if optional_total else 0.5
        prompt_score = _clamp01(prompt_hit_count / max(1.0, min(4.0, float(len(prompt_terms) or 1))))
        normalized = 0.6 * req_score + 0.2 * opt_score + 0.2 * prompt_score
        flags = []
        if required_total and required_hits < required_total:
            flags.append({"type": "missing_required_prompt_points", "missing": required_total - required_hits})
        rationale = "Prompt-relevance score used expected concept coverage and overlap with prompt-specific terms rather than generic semantic similarity."
        return EvaluatorResult(self.evaluator_id, criterion.criterion_id, round(normalized * criterion.max_score, 2), criterion.max_score, 0.78, rationale, [e.evidence_id for e in texts[:4]], flags)


class CounterargumentAwarenessEvaluator(BaseEvaluator):
    evaluator_id = "counterargument_awareness"

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        texts = _text_items(evidence)
        if not texts:
            return EvaluatorResult(self.evaluator_id, criterion.criterion_id, 0.0, criterion.max_score, 0.8, "No text evidence found for counterargument-awareness evaluation.")
        joined = " ".join((t.content or "") for t in texts[:8]).lower()
        concessive = sum(1 for m in ["however", "although", "while", "yet", "nevertheless", "on the other hand", "even though"] if m in joined)
        rebuttal = sum(1 for m in ["but", "still", "nonetheless", "despite", "even so"] if m in joined)
        alternative = sum(1 for m in ["another view", "one might argue", "critics", "opponents", "alternative"] if m in joined)
        normalized = 0.45 * _clamp01(concessive / 2.0) + 0.35 * _clamp01(rebuttal / 2.0) + 0.20 * _clamp01(alternative / 1.0)
        flags = [] if normalized >= 0.35 else [{"type": "limited_nuance_or_counterargument"}]
        rationale = "Counterargument-awareness score used concessive language, acknowledgement of alternative positions, and rebuttal markers."
        return EvaluatorResult(self.evaluator_id, criterion.criterion_id, round(normalized * criterion.max_score, 2), criterion.max_score, 0.74, rationale, [e.evidence_id for e in texts[:4]], flags)


class SourceIntegrationEvaluator(BaseEvaluator):
    evaluator_id = "source_integration"

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        texts = _text_items(evidence)
        if not texts:
            return EvaluatorResult(self.evaluator_id, criterion.criterion_id, 0.0, criterion.max_score, 0.8, "No text evidence found for source-integration evaluation.")
        contents = [(t.content or "") for t in texts[:8]]
        joined = "\n".join(contents).lower()
        citation_hits = len(re.findall(r"\[[0-9]+\]|\([A-Z][A-Za-z\-]+,?\s+\d{4}\)", "\n".join(contents)))
        quote_hits = joined.count('"') // 2
        integration_hits = sum(1 for m in ["this suggests", "this shows", "therefore", "because", "which implies", "reveals", "indicates"] if m in joined)
        attribution_hits = sum(1 for m in ["according to", "the author", "the text", "the passage", "as x argues", "writes that"] if m in joined)
        paragraph_mix = 0
        for c in contents:
            low = c.lower()
            if any(m in low for m in ["according to", "the text", "author", "[", "("]) and any(m in low for m in ["suggests", "shows", "therefore", "because", "reveals"]):
                paragraph_mix += 1
        normalized = 0.20 * _clamp01(citation_hits / 2.0) + 0.15 * _clamp01(quote_hits / 2.0) + 0.25 * _clamp01(attribution_hits / 2.0) + 0.25 * _clamp01(integration_hits / 3.0) + 0.15 * _clamp01(paragraph_mix / 2.0)
        flags = [] if paragraph_mix or integration_hits else [{"type": "source_dropped_without_analysis"}]
        rationale = "Source-integration score distinguished mere citation from actual integration by checking whether attributed material is analytically connected to the student's argument."
        return EvaluatorResult(self.evaluator_id, criterion.criterion_id, round(normalized * criterion.max_score, 2), criterion.max_score, 0.79, rationale, [e.evidence_id for e in texts[:4]], flags)


class DiscourseStructureEvaluator(BaseEvaluator):
    evaluator_id = "discourse_structure"

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        texts = _text_items(evidence)
        if not texts:
            return EvaluatorResult(self.evaluator_id, criterion.criterion_id, 0.0, criterion.max_score, 0.8, "No text evidence found for discourse-structure evaluation.")
        contents = [(t.content or "") for t in texts[:10]]
        para_count = len(contents)
        joined = " ".join(contents).lower()
        intro = 1.0 if any(tok in joined for tok in ["in this essay", "this response", "i argue", "this paper"]) else 0.0
        conclusion = 1.0 if any(tok in joined for tok in ["in conclusion", "to conclude", "overall", "thus", "therefore"]) else 0.0
        transitions = sum(1 for m in ["first", "second", "finally", "however", "moreover", "furthermore", "therefore", "by contrast"] if m in joined)
        paragraph_balance = _clamp01(para_count / 3.0)
        normalized = 0.25 * intro + 0.20 * conclusion + 0.30 * _clamp01(transitions / 4.0) + 0.25 * paragraph_balance
        flags = [] if para_count >= 2 else [{"type": "underdeveloped_structure"}]
        rationale = "Discourse-structure score used paragraph development, transition markers, and weak introduction/conclusion cues."
        return EvaluatorResult(self.evaluator_id, criterion.criterion_id, round(normalized * criterion.max_score, 2), criterion.max_score, 0.73, rationale, [e.evidence_id for e in texts[:5]], flags)


class InterpretiveDepthEvaluator(BaseEvaluator):
    evaluator_id = "interpretive_depth"

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        texts = _text_items(evidence)
        if not texts:
            return EvaluatorResult(self.evaluator_id, criterion.criterion_id, 0.0, criterion.max_score, 0.8, "No text evidence found for interpretive-depth evaluation.")
        joined = " ".join((t.content or "") for t in texts[:8]).lower()
        analysis_markers = sum(1 for m in ["suggests", "implies", "reveals", "signifies", "undermines", "complicates", "therefore", "because"] if m in joined)
        summary_markers = sum(1 for m in ["says", "states", "describes", "talks about", "is about"] if m in joined)
        nuance_markers = sum(1 for m in ["however", "although", "while", "yet", "tension", "ambiguity", "paradox"] if m in joined)
        normalized = 0.5 * _clamp01(analysis_markers / 4.0) + 0.25 * _clamp01(nuance_markers / 2.0) + 0.25 * (1.0 - _clamp01(summary_markers / 4.0))
        flags = [] if analysis_markers else [{"type": "summary_without_interpretation"}]
        rationale = "Interpretive-depth score rewarded analysis and nuance while penalizing purely summary-style writing."
        return EvaluatorResult(self.evaluator_id, criterion.criterion_id, round(normalized * criterion.max_score, 2), criterion.max_score, 0.75, rationale, [e.evidence_id for e in texts[:4]], flags)


class TopologyConstraintSatisfactionEvaluator(BaseEvaluator):
    evaluator_id = "topology_constraint_satisfaction"

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        diagrams = [e for e in evidence if e.modality == "diagram"]
        if not diagrams:
            return EvaluatorResult(self.evaluator_id, criterion.criterion_id, 0.0, criterion.max_score, 0.84, "No diagram/topology evidence was available.", flags=[{"type": "missing_diagram_topology"}])
        metadata = criterion.metadata or {}
        required_components = set(metadata.get("required_components", []))
        accepted_families = set(metadata.get("accepted_families", []))
        expected_topology = metadata.get("expected_topology", {}) or {}
        components = set()
        family = "unknown"
        has_feedback = False
        node_count = 0
        edge_count = 0
        for ev in diagrams:
            sc = ev.structured_content or {}
            components.update(sc.get("detected_components", []))
            family = sc.get("diagram_family", family) or family
            has_feedback = has_feedback or bool(sc.get("has_feedback") or sc.get("functional_plausibility") and 'feedback_path' in components)
            node_count = max(node_count, int(sc.get("node_count_estimate", 0) or sc.get("relation_node_count", 0) or 0))
            edge_count = max(edge_count, int(sc.get("edge_count_estimate", 0) or sc.get("relation_edge_count", 0) or 0))
        component_score = _safe_div(len(required_components & components), len(required_components)) if required_components else 0.75
        family_score = 1.0 if family in accepted_families else (0.65 if family != 'unknown' else 0.35)
        topology_checks = []
        if expected_topology.get('requires_feedback', False):
            topology_checks.append(1.0 if has_feedback else 0.0)
        min_nodes = int(expected_topology.get('min_nodes', 0) or 0)
        min_edges = int(expected_topology.get('min_edges', 0) or 0)
        if min_nodes:
            topology_checks.append(_clamp01(node_count / float(min_nodes)))
        if min_edges:
            topology_checks.append(_clamp01(edge_count / float(min_edges)))
        topology_score = mean(topology_checks) if topology_checks else 0.7
        normalized = 0.4 * component_score + 0.35 * topology_score + 0.25 * family_score
        flags = []
        if family == 'unknown' and component_score >= 0.6 and topology_score >= 0.6:
            flags.append({"type": "unknown_but_structurally_plausible"})
        return EvaluatorResult(
            self.evaluator_id,
            criterion.criterion_id,
            round(_clamp01(normalized) * criterion.max_score, 2),
            criterion.max_score,
            0.78 if family != 'unknown' else 0.68,
            f"Topology score used component coverage, required topology constraints, and recognized-family cues. family={family}, feedback={has_feedback}, nodes={node_count}, edges={edge_count}.",
            [e.evidence_id for e in diagrams[:4]],
            flags,
        )


class AlternativeDesignPlausibilityEvaluator(BaseEvaluator):
    evaluator_id = "alternative_design_plausibility"

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        diagrams = [e for e in evidence if e.modality == 'diagram']
        texts = _text_items(evidence)
        tables = [e for e in evidence if e.modality == 'table']
        if not diagrams:
            return EvaluatorResult(self.evaluator_id, criterion.criterion_id, 0.0, criterion.max_score, 0.82, "No design evidence was available for alternative-design plausibility.")
        joined = ' '.join((t.content or '').lower() for t in texts[:6])
        alt_markers = sum(1 for m in ['alternative', 'nonstandard', 'equivalent', 'valid family', 'different topology', 'one valid'] if m in joined)
        rationale_markers = sum(1 for m in ['because', 'therefore', 'target behavior', 'works', 'satisfies', 'intended behavior'] if m in joined)
        sim_support = 0.0
        for t in tables:
            metrics = (t.structured_content or {}).get('metrics', {}) or {}
            if metrics:
                sim_support = max(sim_support, _clamp01(len(metrics) / 2.0))
        components = set()
        families = set()
        for ev in diagrams:
            sc = ev.structured_content or {}
            components.update(sc.get('detected_components', []))
            fam = sc.get('diagram_family', 'unknown')
            if fam:
                families.add(fam)
        structural = 1.0 if {'input_node', 'output_node'} <= components else (0.65 if components else 0.0)
        normalized = 0.35 * structural + 0.25 * _clamp01(alt_markers / 2.0) + 0.25 * _clamp01(rationale_markers / 3.0) + 0.15 * sim_support
        flags = []
        if 'unknown' in families or not families:
            flags.append({"type": "plausible_alternative_design"})
        return EvaluatorResult(
            self.evaluator_id,
            criterion.criterion_id,
            round(_clamp01(normalized) * criterion.max_score, 2),
            criterion.max_score,
            0.7,
            "Alternative-design plausibility used non-unique-design markers, explicit rationale, simulation support, and minimal structural sanity rather than exact template matching.",
            [e.evidence_id for e in (diagrams[:2] + texts[:2] + tables[:1])],
            flags,
        )


class BehavioralMetricAlignmentEvaluator(BaseEvaluator):
    evaluator_id = "behavioral_metric_alignment"

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        texts = _text_items(evidence)
        tables = [e for e in evidence if e.modality == 'table']
        metadata = criterion.metadata or {}
        expected_metrics = set(m.lower() for m in metadata.get('expected_metrics', []))
        expected_behavior = str(metadata.get('target_behavior', '')).lower()
        joined = ' '.join((t.content or '').lower() for t in texts[:8])
        observed_metrics = {}
        for table in tables:
            observed_metrics.update(((table.structured_content or {}).get('metrics', {}) or {}))
        observed_names = set(k.lower() for k in observed_metrics.keys())
        metric_cov = _safe_div(len(expected_metrics & observed_names), len(expected_metrics)) if expected_metrics else _clamp01(len(observed_names) / 2.0)
        mention_cov = _safe_div(len(expected_metrics & set(tok for tok in _tokenize(joined))), len(expected_metrics)) if expected_metrics else (1.0 if observed_names else 0.0)
        trend_score = 0.0
        headers = []
        rows = []
        for table in tables:
            sc = table.structured_content or {}
            headers = sc.get('header', headers)
            if table.content:
                lines = [ln.strip() for ln in table.content.splitlines() if ln.strip()]
                if len(lines) > 1:
                    for ln in lines[1:6]:
                        rows.append([x.strip() for x in ln.split(',')])
        if expected_behavior == 'low_pass' and rows:
            try:
                freq_idx = [h.lower() for h in headers].index('frequency') if headers else 0
                gain_idx = [h.lower() for h in headers].index('gain') if headers else 1
                pairs = []
                for r in rows:
                    if max(freq_idx, gain_idx) < len(r):
                        pairs.append((float(r[freq_idx]), float(r[gain_idx])))
                if len(pairs) >= 2:
                    pairs.sort()
                    trend_score = 1.0 if pairs[-1][1] < pairs[0][1] else 0.2
            except Exception:
                trend_score = 0.4 if 'low-pass' in joined or 'low pass' in joined else 0.0
        else:
            trend_score = 0.6 if observed_names else 0.0
        normalized = 0.35 * metric_cov + 0.25 * mention_cov + 0.25 * trend_score + 0.15 * (1.0 if tables else 0.0)
        flags = []
        missing = sorted(expected_metrics - observed_names)
        if missing:
            flags.append({"type": "expected_metrics_missing", "metrics": missing})
        return EvaluatorResult(
            self.evaluator_id,
            criterion.criterion_id,
            round(_clamp01(normalized) * criterion.max_score, 2),
            criterion.max_score,
            0.76 if tables else 0.66,
            "Behavioral metric alignment checked whether expected engineering metrics were observed, discussed in the report, and broadly consistent with the target behavior.",
            [e.evidence_id for e in (texts[:2] + tables[:2])],
            flags,
        )


class DesignReportAlignmentEvaluator(BaseEvaluator):
    evaluator_id = "design_report_alignment"

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        texts = _text_items(evidence)
        diagrams = [e for e in evidence if e.modality == 'diagram']
        tables = [e for e in evidence if e.modality == 'table']
        if not texts:
            return EvaluatorResult(self.evaluator_id, criterion.criterion_id, 0.0, criterion.max_score, 0.82, "No report text was available for design-report alignment.")
        joined = ' '.join((t.content or '').lower() for t in texts[:8])
        components = set()
        families = set()
        for ev in diagrams:
            sc = ev.structured_content or {}
            components.update(sc.get('detected_components', []))
            fam = sc.get('diagram_family', 'unknown')
            if fam:
                families.add(fam)
        explained_components = sum(1 for c in ['op_amp', 'resistor', 'capacitor', 'feedback_path', 'input_node', 'output_node'] if c in components and any(tok in joined for tok in [c.replace('_', ' '), c, c.split('_')[0]]))
        metric_mentions = 0
        observed_metrics = set()
        for table in tables:
            observed_metrics.update(((table.structured_content or {}).get('metrics', {}) or {}).keys())
        metric_mentions = sum(1 for m in observed_metrics if str(m).lower() in joined)
        behavior_terms = sum(1 for m in ['low-pass', 'low pass', 'gain', 'cutoff', 'stable', 'feedback', 'topology'] if m in joined)
        normalized = 0.4 * _clamp01(explained_components / 3.0) + 0.25 * _clamp01(metric_mentions / max(1, len(observed_metrics) or 1)) + 0.2 * _clamp01(behavior_terms / 4.0) + 0.15 * (1.0 if diagrams else 0.0)
        return EvaluatorResult(
            self.evaluator_id,
            criterion.criterion_id,
            round(_clamp01(normalized) * criterion.max_score, 2),
            criterion.max_score,
            0.77,
            "Design-report alignment checked whether the written explanation actually names the topology, components, and observed engineering metrics that appear elsewhere in the submission.",
            [e.evidence_id for e in (texts[:3] + diagrams[:2] + tables[:1])],
        )


class LabSetupCompletenessEvaluator(BaseEvaluator):
    evaluator_id = "lab_setup_completeness"

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        texts = _text_items(evidence)
        diagrams = [e for e in evidence if e.modality == 'diagram']
        joined = ' '.join((t.content or '').lower() for t in texts[:10])
        metadata = criterion.metadata or {}
        setup_terms = [str(x).lower() for x in metadata.get('setup_terms', ['apparatus', 'setup', 'connection', 'supply', 'measure', 'instrument'])]
        instrument_terms = [str(x).lower() for x in metadata.get('instrument_terms', ['cro', 'dso', 'multimeter', 'function generator', 'power supply', 'oscilloscope'])]
        setup_cov = _safe_div(sum(1 for t in setup_terms if t in joined), len(setup_terms)) if setup_terms else 0.0
        instrument_cov = _safe_div(sum(1 for t in instrument_terms if t in joined), len(instrument_terms)) if instrument_terms else 0.0
        diagram_bonus = 0.2 if diagrams else 0.0
        normalized = 0.45 * _clamp01(setup_cov) + 0.35 * _clamp01(instrument_cov) + diagram_bonus
        flags = []
        if setup_cov < 0.35:
            flags.append({'type': 'thin_setup_description'})
        if not diagrams:
            flags.append({'type': 'missing_setup_diagram'})
        return EvaluatorResult(self.evaluator_id, criterion.criterion_id, round(_clamp01(normalized) * criterion.max_score, 2), criterion.max_score, 0.79 if texts else 0.72, 'Evaluated whether the engineering-lab submission clearly described apparatus, connections, and measurement setup.', supporting_evidence=[e.evidence_id for e in (texts[:3] + diagrams[:2])], flags=flags)


class ObservationTableQualityEvaluator(BaseEvaluator):
    evaluator_id = "observation_table_quality"

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        tables = [e for e in evidence if e.modality == 'table']
        texts = _text_items(evidence)
        if not tables:
            return EvaluatorResult(self.evaluator_id, criterion.criterion_id, 0.0, criterion.max_score, 0.84, 'No observation/measurement table evidence was available.', flags=[{'type': 'missing_observation_table'}])
        quality = 0.0
        detail_flags = []
        for table in tables:
            sc = table.structured_content or {}
            header = [str(h).strip().lower() for h in sc.get('header', [])]
            row_count = int(sc.get('row_count', 0) or 0)
            metrics = sc.get('metrics', {}) or {}
            has_units = sum(1 for h in header if '(' in h or ')' in h or 'volt' in h or 'amp' in h or 'hz' in h or 'db' in h)
            header_score = _clamp01(len(header) / 4.0)
            row_score = _clamp01(row_count / 5.0)
            metric_score = _clamp01(max(len(metrics), has_units) / 3.0)
            quality = max(quality, 0.35 * header_score + 0.35 * row_score + 0.30 * metric_score)
            if row_count < 3:
                detail_flags.append({'type': 'few_observations'})
            if not has_units:
                detail_flags.append({'type': 'units_not_clear'})
        joined = ' '.join((t.content or '').lower() for t in texts[:5])
        mention_bonus = 0.1 if any(tok in joined for tok in ['observation', 'reading', 'tabulated', 'measured']) else 0.0
        normalized = _clamp01(quality + mention_bonus)
        return EvaluatorResult(self.evaluator_id, criterion.criterion_id, round(normalized * criterion.max_score, 2), criterion.max_score, 0.83, 'Observation-table quality was estimated from headers, units, row count, and measurement detail.', supporting_evidence=[e.evidence_id for e in tables[:3]], flags=detail_flags)


class CalculationCorrectnessEvaluator(BaseEvaluator):
    evaluator_id = "calculation_correctness"

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        texts = _text_items(evidence)
        equations = [e for e in evidence if e.modality == 'equation']
        joined = ' '.join((t.content or '') for t in texts[:8]).lower()
        calc_terms = ['calculation', 'computed', 'formula', 'using', 'therefore', 'substituting', 'gain =', 'error =', 'percentage error', 'vrms', 'vout', 'vin']
        numeric_steps = len(re.findall(r'\d+(?:\.\d+)?', joined))
        symbol_steps = len(re.findall(r'[=±×*/^]', joined))
        eq_bonus = _clamp01(len(equations) / 3.0)
        calc_cov = _safe_div(sum(1 for t in calc_terms if t in joined), len(calc_terms))
        chain_score = _clamp01((numeric_steps / 12.0) + (symbol_steps / 12.0))
        normalized = 0.4 * _clamp01(calc_cov) + 0.35 * chain_score + 0.25 * eq_bonus
        flags = []
        if numeric_steps < 3:
            flags.append({'type': 'few_numeric_steps'})
        return EvaluatorResult(self.evaluator_id, criterion.criterion_id, round(_clamp01(normalized) * criterion.max_score, 2), criterion.max_score, 0.76 if texts or equations else 0.68, 'Calculated from the presence of explicit formulas, substitutions, and multi-step numeric reasoning.', supporting_evidence=[e.evidence_id for e in (texts[:3] + equations[:3])], flags=flags)


class MeasuredExpectedAlignmentEvaluator(BaseEvaluator):
    evaluator_id = "measured_expected_alignment"

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        texts = _text_items(evidence)
        tables = [e for e in evidence if e.modality == 'table']
        joined = ' '.join((t.content or '').lower() for t in texts[:8])
        observed = set()
        for table in tables:
            sc = table.structured_content or {}
            observed.update(str(k).lower() for k in (sc.get('metrics', {}) or {}).keys())
            for key in ['gain', 'cutoff', 'bandwidth', 'phase_margin', 'stability', 'voltage', 'current', 'frequency']:
                if sc.get(key) is not None:
                    observed.add(key)
        metadata = criterion.metadata or {}
        expected_metrics = set(str(x).lower() for x in metadata.get('expected_metrics', []))
        expected_terms = set(str(x).lower() for x in metadata.get('expected_terms', []))
        overlap = _safe_div(len((observed | set(tok for tok in _tokenize(joined) if tok in observed)) & (expected_metrics | expected_terms)), len(expected_metrics | expected_terms)) if (expected_metrics or expected_terms) else _clamp01(len(observed) / 3.0)
        discussion_terms = sum(1 for t in ['expected', 'observed', 'deviation', 'close to', 'matches', 'error', 'difference'] if t in joined)
        normalized = 0.65 * _clamp01(overlap) + 0.35 * _clamp01(discussion_terms / 4.0)
        flags=[]
        if overlap < 0.35:
            flags.append({'type':'measured_expected_mismatch'})
        return EvaluatorResult(self.evaluator_id, criterion.criterion_id, round(_clamp01(normalized) * criterion.max_score,2), criterion.max_score, 0.8 if tables or texts else 0.7, 'Checked whether reported measurements/results align with the expected engineering-lab behavior.', supporting_evidence=[e.evidence_id for e in (tables[:3]+texts[:3])], flags=flags)


class ErrorAnalysisQualityEvaluator(BaseEvaluator):
    evaluator_id = "error_analysis_quality"

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        texts = _text_items(evidence)
        joined = ' '.join((t.content or '').lower() for t in texts[:8])
        error_terms = ['error', 'percentage error', 'deviation', 'tolerance', 'experimental error', 'source of error', 'uncertainty', 'instrument error', 'loading effect']
        mitigation_terms = ['precaution', 'reduce', 'avoid', 'calibrate', 'repeat', 'carefully']
        explanation_terms = ['because', 'due to', 'therefore', 'caused by', 'reason']
        error_score = _safe_div(sum(1 for t in error_terms if t in joined), len(error_terms))
        mitigation_score = _safe_div(sum(1 for t in mitigation_terms if t in joined), len(mitigation_terms))
        explanation_score = _clamp01(sum(1 for t in explanation_terms if t in joined) / 4.0)
        normalized = 0.5 * _clamp01(error_score) + 0.25 * _clamp01(mitigation_score) + 0.25 * explanation_score
        flags=[]
        if error_score < 0.25:
            flags.append({'type':'weak_error_analysis'})
        return EvaluatorResult(self.evaluator_id, criterion.criterion_id, round(_clamp01(normalized)*criterion.max_score,2), criterion.max_score, 0.78 if texts else 0.68, 'Assessed whether the report discusses deviations, likely causes, and precautions/error mitigation.', supporting_evidence=[e.evidence_id for e in texts[:4]], flags=flags)


class SimulationHardwareAlignmentEvaluator(BaseEvaluator):
    evaluator_id = "simulation_hardware_alignment"

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        texts = _text_items(evidence)
        tables = [e for e in evidence if e.modality == 'table']
        joined = ' '.join((t.content or '').lower() for t in texts[:10])
        sim_terms = ['simulation', 'ltspice', 'multisim', 'proteus', 'theoretical']
        hw_terms = ['hardware', 'measured', 'experimental', 'breadboard', 'implemented']
        compare_terms = ['compare', 'compared', 'difference', 'deviation', 'close to', 'matches', 'variation']
        sim_score = _clamp01(sum(1 for t in sim_terms if t in joined) / 3.0)
        hw_score = _clamp01(sum(1 for t in hw_terms if t in joined) / 3.0)
        compare_score = _clamp01(sum(1 for t in compare_terms if t in joined) / 3.0)
        metric_bonus = 0.0
        if tables:
            for tb in tables:
                metrics = (tb.structured_content or {}).get('metrics', {}) or {}
                if metrics:
                    metric_bonus = max(metric_bonus, _clamp01(len(metrics)/3.0))
        normalized = 0.3 * sim_score + 0.3 * hw_score + 0.25 * compare_score + 0.15 * metric_bonus
        flags=[]
        if sim_score > 0.2 and hw_score > 0.2 and compare_score < 0.2:
            flags.append({'type':'sim_hw_not_compared'})
        return EvaluatorResult(self.evaluator_id, criterion.criterion_id, round(_clamp01(normalized)*criterion.max_score,2), criterion.max_score, 0.79 if texts else 0.7, 'Assessed whether simulation/theoretical results were meaningfully compared with hardware or measured observations.', supporting_evidence=[e.evidence_id for e in (texts[:4]+tables[:2])], flags=flags)


class WaveformInterpretationEvaluator(BaseEvaluator):
    evaluator_id = "waveform_interpretation"

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        texts = _text_items(evidence)
        images = [e for e in evidence if e.modality in {'image','plot'}]
        joined = ' '.join((t.content or '').lower() for t in texts[:10])
        waveform_terms = ['waveform', 'time period', 'amplitude', 'frequency', 'phase', 'sine', 'square', 'triangular', 'spectrum']
        axis_terms = ['time', 'voltage', 'amplitude', 'frequency', 'db', 'hz']
        discussion_terms = ['observed', 'therefore', 'indicates', 'peak', 'bandwidth', 'carrier', 'modulated', 'demodulated']
        wf = _clamp01(sum(1 for t in waveform_terms if t in joined) / 4.0)
        ax = _clamp01(sum(1 for t in axis_terms if t in joined) / 3.0)
        ds = _clamp01(sum(1 for t in discussion_terms if t in joined) / 4.0)
        img_bonus = 0.2 if images else 0.0
        normalized = _clamp01(0.4*wf + 0.25*ax + 0.25*ds + img_bonus)
        flags=[]
        if wf < 0.25:
            flags.append({'type':'weak_waveform_interpretation'})
        return EvaluatorResult(self.evaluator_id, criterion.criterion_id, round(normalized*criterion.max_score,2), criterion.max_score, 0.77 if texts or images else 0.65, 'Assessed whether waveform/spectrum evidence is interpreted with relevant signal terms, axes, and conclusions.', supporting_evidence=[e.evidence_id for e in (texts[:4]+images[:2])], flags=flags)


class SpectrumMetricAlignmentEvaluator(BaseEvaluator):
    evaluator_id = "spectrum_metric_alignment"

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        texts = _text_items(evidence)
        tables = [e for e in evidence if e.modality == 'table']
        joined = ' '.join((t.content or '').lower() for t in texts[:10])
        metadata = criterion.metadata or {}
        expected_metrics = set(str(x).lower() for x in metadata.get('expected_metrics', ['snr','ber','bandwidth','gain','frequency']))
        observed = set(tok for tok in _tokenize(joined) if tok in expected_metrics)
        for tb in tables:
            sc = tb.structured_content or {}
            observed.update(str(k).lower() for k in (sc.get('metrics', {}) or {}).keys())
        overlap = _safe_div(len(observed & expected_metrics), len(expected_metrics)) if expected_metrics else 0.0
        compare_terms = _clamp01(sum(1 for t in ['measured','expected','simulated','observed','deviation','close'] if t in joined)/3.0)
        normalized = _clamp01(0.65*overlap + 0.35*compare_terms)
        return EvaluatorResult(self.evaluator_id, criterion.criterion_id, round(normalized*criterion.max_score,2), criterion.max_score, 0.8 if texts or tables else 0.68, 'Checked whether communication/VLSI metrics discussed in the report align with observed or tabulated metrics.', supporting_evidence=[e.evidence_id for e in (texts[:4]+tables[:2])])


class TimingDiagramCorrectnessEvaluator(BaseEvaluator):
    evaluator_id = "timing_diagram_correctness"

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        texts = _text_items(evidence)
        diagrams = [e for e in evidence if e.modality in {'diagram','image'}]
        relation_graphs = [e for e in evidence if e.modality == 'diagram' and e.subtype == 'relation_graph']
        joined = ' '.join((t.content or '').lower() for t in texts[:10])
        timing_terms = ['clock', 'edge', 'posedge', 'negedge', 'setup time', 'hold time', 'delay', 'transition', 'timing']
        logic_terms = ['q', 'clk', 'd', 'reset', 'enable', 'state']
        tt = _clamp01(sum(1 for t in timing_terms if t in joined) / 3.0)
        lt = _clamp01(sum(1 for t in logic_terms if t in joined) / 3.0)
        rg_bonus = 0.0
        rg_flags = []
        if relation_graphs:
            graph = relation_graphs[0].structured_content or {}
            family = graph.get('family', '')
            node_count = int(graph.get('node_count', 0) or 0)
            edge_count = int(graph.get('edge_count', 0) or 0)
            relation_types = set(graph.get('relation_types', []) or [])
            fam_score = 1.0 if family == 'timing_diagram' else (0.55 if edge_count else 0.0)
            structure_score = 0.5 * _clamp01(node_count / 3.0) + 0.5 * _clamp01(edge_count / 2.0)
            relation_score = 1.0 if 'signal_timing_relation' in relation_types else (0.4 if relation_types else 0.0)
            rg_bonus = 0.35 * fam_score + 0.4 * structure_score + 0.25 * relation_score
            if family != 'timing_diagram' and edge_count == 0:
                rg_flags.append({'type':'weak_timing_relation_graph'})
        diag_bonus = 0.1 if diagrams else 0.0
        normalized = _clamp01(0.28*tt + 0.22*lt + 0.40*rg_bonus + diag_bonus)
        flags=[]
        if tt < 0.2 and rg_bonus < 0.2:
            flags.append({'type':'weak_timing_discussion'})
        flags.extend(rg_flags)
        supporting = texts[:4] + relation_graphs[:2] + diagrams[:1]
        return EvaluatorResult(self.evaluator_id, criterion.criterion_id, round(normalized*criterion.max_score,2), criterion.max_score, 0.8 if texts or relation_graphs else 0.64, 'Assessed timing-diagram correctness from timing terminology, signal naming, and extracted relation-graph structure.', supporting_evidence=[e.evidence_id for e in supporting], flags=flags)


class HDLBehaviorConsistencyEvaluator(BaseEvaluator):
    evaluator_id = "hdl_behavior_consistency"

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        codes = _code_items(evidence)
        texts = _text_items(evidence)
        code_joined = ' '.join((c.content or '').lower() for c in codes[:6])
        text_joined = ' '.join((t.content or '').lower() for t in texts[:6])
        hdl_terms = ['module', 'entity', 'always', 'assign', 'process', 'posedge', 'negedge', 'signal']
        behavior_terms = ['truth table', 'state', 'output', 'sequence', 'counter', 'flip-flop', 'fsm']
        hs = _clamp01(sum(1 for t in hdl_terms if t in code_joined) / 3.0)
        bs = _clamp01(sum(1 for t in behavior_terms if t in text_joined or t in code_joined) / 3.0)
        alignment = _clamp01(sum(1 for t in ['counter','shift','mux','decoder','fsm','flip-flop'] if t in code_joined and t in text_joined) / 2.0)
        normalized = _clamp01(0.4*hs + 0.3*bs + 0.3*alignment)
        return EvaluatorResult(self.evaluator_id, criterion.criterion_id, round(normalized*criterion.max_score,2), criterion.max_score, 0.82 if codes else 0.68, 'Checked whether HDL/code artifacts and the written description indicate consistent digital behavior.', supporting_evidence=[e.evidence_id for e in (codes[:3]+texts[:3])])


class ExpectedVsSimulatedBehaviorEvaluator(BaseEvaluator):
    evaluator_id = "expected_vs_simulated_behavior"

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        texts = _text_items(evidence)
        tables = [e for e in evidence if e.modality == 'table']
        joined = ' '.join((t.content or '').lower() for t in texts[:10])
        compare_terms = ['expected', 'simulated', 'observed', 'matches', 'deviation', 'difference', 'close to']
        metric_terms = ['snr','ber','gain','bandwidth','delay','frequency','power']
        compare_score = _clamp01(sum(1 for t in compare_terms if t in joined)/3.0)
        metric_score = _clamp01(sum(1 for t in metric_terms if t in joined)/3.0)
        table_bonus = 0.2 if tables else 0.0
        normalized = _clamp01(0.45*compare_score + 0.35*metric_score + table_bonus)
        return EvaluatorResult(self.evaluator_id, criterion.criterion_id, round(normalized*criterion.max_score,2), criterion.max_score, 0.78 if texts or tables else 0.66, 'Assessed whether expected and simulated/observed communication/VLSI behavior were compared explicitly.', supporting_evidence=[e.evidence_id for e in (texts[:4]+tables[:2])])


class DigitalTruthTableConsistencyEvaluator(BaseEvaluator):
    evaluator_id = "digital_truth_table_consistency"

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        texts = _text_items(evidence)
        tables = [e for e in evidence if e.modality == 'table']
        joined = ' '.join((t.content or '').lower() for t in texts[:10])
        truth_terms = ['truth table', 'state table', 'input', 'output', 'logic 0', 'logic 1']
        logic_terms = ['and', 'or', 'not', 'xor', 'flip-flop', 'counter', 'state']
        tt = _clamp01(sum(1 for t in truth_terms if t in joined)/2.0)
        lt = _clamp01(sum(1 for t in logic_terms if t in joined)/3.0)
        table_bonus = 0.25 if tables else 0.0
        normalized = _clamp01(0.4*tt + 0.35*lt + table_bonus)
        return EvaluatorResult(self.evaluator_id, criterion.criterion_id, round(normalized*criterion.max_score,2), criterion.max_score, 0.77 if texts or tables else 0.65, 'Checked whether truth-table/state-table style digital behavior is documented consistently.', supporting_evidence=[e.evidence_id for e in (texts[:4]+tables[:2])])


class HardwareSoftwareAlignmentEvaluator(BaseEvaluator):
    evaluator_id = "hardware_software_alignment"

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        codes = _code_items(evidence)
        texts = _text_items(evidence)
        execs = _execution_items(evidence)
        code_joined = ' '.join((c.content or '').lower() for c in codes[:6])
        text_joined = ' '.join((t.content or '').lower() for t in texts[:6])
        pairs = [('gpio','pin'), ('interrupt','interrupt'), ('timer','timer'), ('uart','serial'), ('i2c','sensor'), ('spi','display'), ('pwm','motor')]
        matches = sum(1 for a,b in pairs if a in code_joined and b in text_joined)
        exec_bonus = 0.2 if execs else 0.0
        normalized = _clamp01(_safe_div(matches, 3.0) + exec_bonus)
        return EvaluatorResult(self.evaluator_id, criterion.criterion_id, round(normalized*criterion.max_score,2), criterion.max_score, 0.83 if codes else 0.68, 'Checked whether embedded code, report language, and observed execution describe the same hardware behavior.', supporting_evidence=[e.evidence_id for e in (codes[:3]+texts[:3]+execs[:2])])


class PeripheralConfigurationCorrectnessEvaluator(BaseEvaluator):
    evaluator_id = "peripheral_configuration_correctness"

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        codes = _code_items(evidence)
        code_joined = ' '.join((c.content or '').lower() for c in codes[:6])
        cfg_terms = ['gpio', 'pinmode', 'uart', 'spi', 'i2c', 'adc', 'pwm', 'timer', 'interrupt']
        init_terms = ['init', 'setup', 'begin', 'configure', 'enable']
        cfg = _clamp01(sum(1 for t in cfg_terms if t in code_joined) / 4.0)
        init = _clamp01(sum(1 for t in init_terms if t in code_joined) / 3.0)
        normalized = _clamp01(0.6*cfg + 0.4*init)
        return EvaluatorResult(self.evaluator_id, criterion.criterion_id, round(normalized*criterion.max_score,2), criterion.max_score, 0.82 if codes else 0.66, 'Assessed whether the code shows plausible peripheral configuration and initialization patterns.', supporting_evidence=[e.evidence_id for e in codes[:4]])


class SensorActuatorBehaviorEvaluator(BaseEvaluator):
    evaluator_id = "sensor_actuator_behavior"

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        texts = _text_items(evidence)
        codes = _code_items(evidence)
        joined = ' '.join((t.content or '').lower() for t in texts[:8]) + ' ' + ' '.join((c.content or '').lower() for c in codes[:6])
        sensor_terms = ['sensor', 'temperature', 'distance', 'adc', 'read', 'sample']
        actuator_terms = ['motor', 'led', 'buzzer', 'servo', 'display', 'pwm', 'write']
        reaction_terms = ['when', 'if', 'threshold', 'changes', 'responds', 'turns on', 'turns off']
        ss = _clamp01(sum(1 for t in sensor_terms if t in joined)/3.0)
        aa = _clamp01(sum(1 for t in actuator_terms if t in joined)/3.0)
        rs = _clamp01(sum(1 for t in reaction_terms if t in joined)/3.0)
        normalized = _clamp01(0.35*ss + 0.35*aa + 0.3*rs)
        return EvaluatorResult(self.evaluator_id, criterion.criterion_id, round(normalized*criterion.max_score,2), criterion.max_score, 0.79 if texts or codes else 0.65, 'Assessed whether the embedded submission describes plausible sensor/actuator behavior and response logic.', supporting_evidence=[e.evidence_id for e in (texts[:4]+codes[:3])])


class SerialLogBehaviorAlignmentEvaluator(BaseEvaluator):
    evaluator_id = "serial_log_behavior_alignment"

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        texts = _text_items(evidence)
        joined = ' '.join((t.content or '').lower() for t in texts[:10])
        serial_terms = ['serial', 'uart', 'log', 'print', 'debug', 'received', 'transmitted']
        status_terms = ['ok', 'success', 'error', 'timeout', 'value', 'reading']
        ss = _clamp01(sum(1 for t in serial_terms if t in joined)/3.0)
        st = _clamp01(sum(1 for t in status_terms if t in joined)/3.0)
        penalty = 0.2 if joined.count('error') > 2 else 0.0
        normalized = _clamp01(0.55*ss + 0.45*st - penalty)
        return EvaluatorResult(self.evaluator_id, criterion.criterion_id, round(normalized*criterion.max_score,2), criterion.max_score, 0.74 if texts else 0.6, 'Assessed whether serial/log evidence supports the claimed embedded runtime behavior.', supporting_evidence=[e.evidence_id for e in texts[:4]])


class StateMachineBehaviorEvaluator(BaseEvaluator):
    evaluator_id = "state_machine_behavior"

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        texts = _text_items(evidence)
        codes = _code_items(evidence)
        joined = ' '.join((t.content or '').lower() for t in texts[:8]) + ' ' + ' '.join((c.content or '').lower() for c in codes[:6])
        state_terms = ['state', 'transition', 'idle', 'wait', 'run', 'next state', 'fsm', 'switch case']
        event_terms = ['event', 'button', 'interrupt', 'timer', 'condition', 'threshold']
        s1 = _clamp01(sum(1 for t in state_terms if t in joined)/3.0)
        s2 = _clamp01(sum(1 for t in event_terms if t in joined)/3.0)
        normalized = _clamp01(0.6*s1 + 0.4*s2)
        return EvaluatorResult(self.evaluator_id, criterion.criterion_id, round(normalized*criterion.max_score,2), criterion.max_score, 0.8 if texts or codes else 0.64, 'Checked whether the embedded system behavior is described in state/event terms consistent with a finite-state implementation.', supporting_evidence=[e.evidence_id for e in (texts[:4]+codes[:3])])


class PlotInterpretationEvaluator(BaseEvaluator):
    evaluator_id = "plot_interpretation"

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        plots = [e for e in evidence if e.modality == "plot"]
        if not plots:
            return EvaluatorResult(self.evaluator_id, criterion.criterion_id, 0.0, criterion.max_score, 0.7, "No plot-analysis evidence found.")
        scores = []
        for p in plots:
            sc = p.structured_content or {}
            axes = set(sc.get("axes", []))
            labels = set(sc.get("labels", []))
            curves = sc.get("curves", [])
            metric_tokens = set(sc.get("metric_tokens", []))
            s = 0.35 * _clamp01(len(axes) / 2.0) + 0.35 * _clamp01(len(curves)) + 0.15 * _clamp01(len(labels) / 4.0) + 0.15 * _clamp01(len(metric_tokens) / 2.0)
            scores.append(s)
        normalized = mean(scores)
        return EvaluatorResult(self.evaluator_id, criterion.criterion_id, round(normalized * criterion.max_score, 2), criterion.max_score, 0.78, "Assessed whether plots contain recognizable axes, labels, and at least one meaningful curve.", supporting_evidence=[e.evidence_id for e in plots[:4]])


class ObservationSheetUnderstandingEvaluator(BaseEvaluator):
    evaluator_id = "observation_sheet_understanding"

    def evaluate(self, criterion: Criterion, evidence: Sequence[EvidenceObject]) -> EvaluatorResult:
        tables = [e for e in evidence if e.modality == "table" and e.subtype in {"observation_sheet", "observation_summary"}]
        if not tables:
            return EvaluatorResult(self.evaluator_id, criterion.criterion_id, 0.0, criterion.max_score, 0.72, "No observation-sheet evidence found.")
        scores = []
        for t in tables:
            sc = t.structured_content or {}
            if t.subtype == "observation_sheet":
                header = [str(h).lower() for h in sc.get("header", [])]
                rows = sc.get("rows", 0)
                has_expected = any(h in {"expected", "theoretical"} for h in header)
                has_measured = any(h in {"measured", "observed", "reading"} for h in header)
                s = 0.3 * _clamp01(rows / 5.0) + 0.35 * float(has_expected) + 0.35 * float(has_measured)
            else:
                trial_count = sc.get("trial_count", 0)
                has_pairs = bool(sc.get("has_expected_measured_pairs"))
                avg_dev = sc.get("avg_abs_deviation")
                deviation_term = 0.6 if avg_dev is not None else 0.2
                s = 0.35 * _clamp01(trial_count / 5.0) + 0.35 * float(has_pairs) + 0.30 * deviation_term
            scores.append(s)
        normalized = mean(scores)
        return EvaluatorResult(self.evaluator_id, criterion.criterion_id, round(normalized * criterion.max_score, 2), criterion.max_score, 0.82, "Assessed whether the observation sheet includes repeated readings and expected-versus-measured structure.", supporting_evidence=[e.evidence_id for e in tables[:4]])
