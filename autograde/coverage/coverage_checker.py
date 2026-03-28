from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from autograde.coverage.aspect_model import AspectCoverageResult, CoverageAssessment, CriterionAspect
from autograde.executor.evidence_query import EvidenceBundle
from autograde.models import EvidenceObject
from autograde.rubric.schema import Criterion


@dataclass(slots=True)
class _MatchedEvidence:
    evidence: List[EvidenceObject]
    rationale_bits: List[str]


class CoverageChecker:
    _MODALITY_ALIASES = {
        'report': {'report', 'text', 'essay'},
        'text': {'text', 'report', 'essay'},
        'code': {'code', 'source_code', 'execution'},
        'source_code': {'source_code', 'code', 'execution'},
        'execution': {'execution', 'code', 'source_code'},
        'diagram': {'diagram', 'design_diagram', 'image'},
        'image': {'image', 'diagram', 'design_diagram'},
        'figure': {'image', 'diagram'},
        'table': {'table'},
        'citation': {'citation', 'text'},
    }

    def assess(self, criterion: Criterion, evidence_bundle: EvidenceBundle) -> CoverageAssessment:
        aspects = list(getattr(criterion, 'aspects', []) or [])
        if not aspects:
            return self._fallback_assessment(criterion, evidence_bundle)

        results: List[AspectCoverageResult] = []
        flags = []
        missing_required: List[str] = []
        weak_required: List[str] = []
        scores: List[float] = []
        order = {'covered': 1.0, 'weakly_covered': 0.6, 'unsupported': 0.35, 'missing': 0.0, 'contradicted': 0.0}

        for aspect in aspects:
            matched = self._match_aspect(aspect, evidence_bundle.evidence)
            if len(matched.evidence) >= max(1, aspect.min_evidence_count):
                avg_conf = sum(e.confidence for e in matched.evidence) / len(matched.evidence)
                if avg_conf >= 0.7:
                    status = 'covered'
                else:
                    status = 'weakly_covered'
                rationale = f"Aspect '{aspect.aspect_id}' was supported by {len(matched.evidence)} evidence item(s)."
                if matched.rationale_bits:
                    rationale += ' Matched via ' + ', '.join(matched.rationale_bits[:3]) + '.'
                evidence_ids = [e.evidence_id for e in matched.evidence]
                confidence = round(avg_conf, 3)
            elif matched.evidence:
                status = 'weakly_covered'
                rationale = f"Aspect '{aspect.aspect_id}' had partial evidence but not enough to satisfy the minimum count."
                evidence_ids = [e.evidence_id for e in matched.evidence]
                confidence = round(sum(e.confidence for e in matched.evidence) / len(matched.evidence), 3)
            else:
                status = 'missing'
                rationale = f"Aspect '{aspect.aspect_id}' had no matching evidence."
                evidence_ids = []
                confidence = 0.0

            if status == 'missing' and aspect.required:
                missing_required.append(aspect.aspect_id)
                flags.append({'type': 'missing_required_aspect', 'aspect_id': aspect.aspect_id})
            elif status == 'weakly_covered' and aspect.required:
                weak_required.append(aspect.aspect_id)
                flags.append({'type': 'weak_required_aspect', 'aspect_id': aspect.aspect_id})

            scores.append(order[status])
            results.append(AspectCoverageResult(
                aspect_id=aspect.aspect_id,
                status=status,
                rationale=rationale,
                evidence_ids=evidence_ids,
                confidence=confidence,
            ))

        coverage_score = round(sum(scores) / len(scores), 3) if scores else 0.0
        if missing_required:
            overall_status = 'missing_required'
            rationale = 'Some required rubric aspects were missing.'
        elif weak_required:
            overall_status = 'partial'
            rationale = 'Required rubric aspects were present but some were only weakly covered.'
        else:
            overall_status = 'covered'
            rationale = 'All rubric aspects were adequately covered.'

        return CoverageAssessment(
            overall_status=overall_status,
            coverage_score=coverage_score,
            rationale=rationale,
            aspect_results=results,
            missing_required=missing_required,
            weak_required=weak_required,
            flags=flags,
        )

    def _fallback_assessment(self, criterion: Criterion, evidence_bundle: EvidenceBundle) -> CoverageAssessment:
        # Preserve old behavior when aspect model is absent.
        evidence = list(evidence_bundle.evidence)
        if not evidence:
            return CoverageAssessment(
                overall_status='missing_required',
                coverage_score=0.0,
                rationale='No evidence available for criterion coverage.',
                flags=[{'type': 'missing_required_aspect', 'aspect_id': 'default'}],
                missing_required=['default'],
            )
        direct_count = len(evidence_bundle.direct_ids)
        if direct_count >= max(1, criterion.minimum_evidence_count):
            return CoverageAssessment(
                overall_status='covered',
                coverage_score=1.0,
                rationale='Coverage fallback considered the matched direct evidence sufficient.',
            )
        return CoverageAssessment(
            overall_status='partial',
            coverage_score=0.6,
            rationale='Coverage fallback found evidence, but not enough direct evidence to fully satisfy the criterion.',
            weak_required=['default'],
            flags=[{'type': 'weak_required_aspect', 'aspect_id': 'default'}],
        )

    def _match_aspect(self, aspect: CriterionAspect, evidence: Iterable[EvidenceObject]) -> _MatchedEvidence:
        matched: List[EvidenceObject] = []
        rationale_bits: List[str] = []
        allowed_modalities = set()
        for modality in aspect.modalities:
            allowed_modalities.add(modality)
            allowed_modalities.update(self._MODALITY_ALIASES.get(modality, set()))
        required_types = set(aspect.evidence_types)
        required_tags = set(aspect.tags)

        for ev in evidence:
            modality_ok = not allowed_modalities or ev.modality in allowed_modalities or ev.subtype in allowed_modalities
            type_ok = not required_types or ev.subtype in required_types
            tag_ok = not required_tags or bool(required_tags.intersection(ev.tags))
            if modality_ok and type_ok and tag_ok:
                matched.append(ev)
                if required_types and ev.subtype in required_types:
                    rationale_bits.append(f"subtype:{ev.subtype}")
                elif required_tags and required_tags.intersection(ev.tags):
                    rationale_bits.append(f"tag:{sorted(required_tags.intersection(ev.tags))[0]}")
                elif allowed_modalities:
                    rationale_bits.append(f"modality:{ev.modality}")
        return _MatchedEvidence(evidence=matched, rationale_bits=rationale_bits)
