from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List

from autograde.models import EvidenceObject, Submission
from autograde.rubric.compiler import EvidenceQueryPlan


@dataclass(slots=True)
class EvidenceBundle:
    evidence: List[EvidenceObject] = field(default_factory=list)
    direct_ids: List[str] = field(default_factory=list)
    supporting_ids: List[str] = field(default_factory=list)
    missing_requirements: List[str] = field(default_factory=list)
    query_summary: str = ""

    def __iter__(self):
        return iter(self.evidence)

    def __len__(self):
        return len(self.evidence)


class EvidenceQueryEngine:
    _ARTIFACT_ALIASES = {
        "report": {"report", "text", "essay"},
        "text": {"text", "report", "essay"},
        "code": {"code", "source_code", "execution"},
        "source_code": {"source_code", "code", "execution"},
        "execution": {"execution", "code", "source_code"},
        "diagram": {"diagram", "design_diagram", "image"},
        "image": {"image", "diagram", "design_diagram"},
    }

    def query(self, submission: Submission, plan: EvidenceQueryPlan) -> EvidenceBundle:
        artifact_map = {a.artifact_id: a for a in submission.artifacts}
        direct: list[EvidenceObject] = []
        supporting: list[EvidenceObject] = []

        for ev in submission.evidence:
            if plan.required_modalities:
                allowed_modalities = set()
                for modality in plan.required_modalities:
                    allowed_modalities.add(modality)
                    allowed_modalities.update(self._ARTIFACT_ALIASES.get(modality, set()))
                if ev.modality not in allowed_modalities:
                    continue
            art = artifact_map.get(ev.artifact_id)
            if plan.artifact_scope:
                allowed = set(plan.artifact_scope)
                expanded_allowed = set(allowed)
                for item in list(allowed):
                    expanded_allowed.update(self._ARTIFACT_ALIASES.get(item, set()))
                if not (art and art.artifact_type in expanded_allowed) and ev.modality not in expanded_allowed and ev.subtype not in expanded_allowed:
                    continue
            tag_set = set(ev.tags)
            if plan.required_evidence_types and ev.subtype in plan.required_evidence_types:
                direct.append(ev)
                continue
            if plan.required_tags and tag_set.intersection(plan.required_tags):
                direct.append(ev)
                continue
            if plan.supporting_evidence_types and ev.subtype in plan.supporting_evidence_types:
                supporting.append(ev)
                continue
            if plan.supporting_tags and tag_set.intersection(plan.supporting_tags):
                supporting.append(ev)
                continue
            if not plan.required_evidence_types and not plan.required_tags:
                direct.append(ev)

        all_evidence = direct + [e for e in supporting if e.evidence_id not in {d.evidence_id for d in direct}]
        missing: list[str] = []
        if plan.required_evidence_types:
            present_subtypes = {e.subtype for e in direct}
            missing.extend(sorted(set(plan.required_evidence_types) - present_subtypes))
        if plan.required_tags:
            present_tags = set(tag for e in direct for tag in e.tags)
            missing.extend(sorted(set(plan.required_tags) - present_tags))
        if len(direct) < plan.minimum_evidence_count:
            missing.append(f"minimum_evidence_count<{plan.minimum_evidence_count}")

        return EvidenceBundle(
            evidence=all_evidence,
            direct_ids=[e.evidence_id for e in direct],
            supporting_ids=[e.evidence_id for e in supporting],
            missing_requirements=missing,
            query_summary=f"direct={len(direct)}, supporting={len(supporting)}, total={len(all_evidence)}",
        )
