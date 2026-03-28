from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from statistics import mean, median, pstdev
from typing import Any, Dict, List, Sequence

from autograde.models import GradingResult


@dataclass(slots=True)
class CohortSubmissionRecord:
    submission_id: str
    student_id: str | None
    subject_id: str
    template_id: str | None
    grading_result: GradingResult


@dataclass(slots=True)
class CohortAnalysis:
    total_submissions: int
    average_score: float
    median_score: float
    score_std: float
    average_confidence: float
    review_rate: float
    priority_review_counts: Dict[str, int] = field(default_factory=dict)
    subject_breakdown: Dict[str, Dict[str, float]] = field(default_factory=dict)
    plagiarism_clusters: List[Dict[str, Any]] = field(default_factory=list)
    prioritized_review_queue: List[Dict[str, Any]] = field(default_factory=list)
    anomalous_submissions: List[Dict[str, Any]] = field(default_factory=list)


class CohortAnalyzer:
    def analyze(
        self,
        records: Sequence[CohortSubmissionRecord],
        cohort_flags: Sequence[Dict[str, Any]] | None = None,
    ) -> CohortAnalysis:
        if not records:
            return CohortAnalysis(0, 0.0, 0.0, 0.0, 0.0, 0.0)

        cohort_flags = list(cohort_flags or [])
        scores = [r.grading_result.final_score for r in records]
        confidences = [self._avg_conf(r.grading_result) for r in records]
        review_rate = sum(1 for r in records if r.grading_result.review_bundles) / len(records)

        subject_breakdown = self._subject_breakdown(records)
        plagiarism_clusters = self._build_clusters(cohort_flags)
        prioritized_review_queue = self._prioritize_review_queue(records, cohort_flags)
        anomalous_submissions = self._find_anomalies(records)
        priority_review_counts = self._review_priority_counts(prioritized_review_queue)

        return CohortAnalysis(
            total_submissions=len(records),
            average_score=round(mean(scores), 2),
            median_score=round(median(scores), 2),
            score_std=round(pstdev(scores) if len(scores) > 1 else 0.0, 3),
            average_confidence=round(mean(confidences), 3),
            review_rate=round(review_rate, 3),
            priority_review_counts=priority_review_counts,
            subject_breakdown=subject_breakdown,
            plagiarism_clusters=plagiarism_clusters,
            prioritized_review_queue=prioritized_review_queue,
            anomalous_submissions=anomalous_submissions,
        )

    @staticmethod
    def _avg_conf(result: GradingResult) -> float:
        if not result.criterion_results:
            return 0.0
        return mean(cr.confidence for cr in result.criterion_results)

    def _subject_breakdown(self, records: Sequence[CohortSubmissionRecord]) -> Dict[str, Dict[str, float]]:
        by_subject: Dict[str, List[CohortSubmissionRecord]] = defaultdict(list)
        for rec in records:
            by_subject[rec.subject_id].append(rec)
        out: Dict[str, Dict[str, float]] = {}
        for subject, group in by_subject.items():
            scores = [g.grading_result.final_score for g in group]
            confs = [self._avg_conf(g.grading_result) for g in group]
            out[subject] = {
                'count': float(len(group)),
                'avg_score': round(mean(scores), 2),
                'median_score': round(median(scores), 2),
                'avg_confidence': round(mean(confs), 3),
                'review_rate': round(sum(1 for g in group if g.grading_result.review_bundles) / len(group), 3),
                'high_priority_reviews': float(sum(1 for g in group for rb in g.grading_result.review_bundles if rb.get('priority') in {'high', 'critical'})),
            }
        return out

    def _build_clusters(self, cohort_flags: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        pair_graph: Dict[str, set[str]] = defaultdict(set)
        explicit_clusters: List[Dict[str, Any]] = []
        for flag in cohort_flags:
            typ = flag.get('type')
            if typ == 'intra_cohort_similarity':
                a, b = flag.get('submission_a'), flag.get('submission_b')
                if a and b:
                    pair_graph[str(a)].add(str(b))
                    pair_graph[str(b)].add(str(a))
            elif typ == 'intra_cohort_cluster':
                members = [m for m in str(flag.get('members', '')).split(',') if m]
                explicit_clusters.append({
                    'members': members,
                    'severity': flag.get('severity', 'high'),
                    'confidence': float(flag.get('confidence', 0.0) or 0.0),
                    'message': flag.get('message', ''),
                })
        seen: set[str] = set()
        derived: List[Dict[str, Any]] = []
        for node in pair_graph:
            if node in seen:
                continue
            stack = [node]
            comp: List[str] = []
            while stack:
                cur = stack.pop()
                if cur in seen:
                    continue
                seen.add(cur)
                comp.append(cur)
                stack.extend(sorted(pair_graph[cur] - seen))
            if len(comp) >= 3:
                derived.append({
                    'members': sorted(comp),
                    'severity': 'high',
                    'confidence': 0.8,
                    'message': 'Derived suspicious similarity component in cohort.',
                })
        by_key: Dict[tuple[str, ...], Dict[str, Any]] = {}
        for cluster in explicit_clusters + derived:
            key = tuple(sorted(cluster['members']))
            prev = by_key.get(key)
            if prev is None or float(cluster.get('confidence', 0.0)) > float(prev.get('confidence', 0.0)):
                by_key[key] = cluster
        return sorted(by_key.values(), key=lambda c: (-len(c['members']), -float(c.get('confidence', 0.0))))

    def _prioritize_review_queue(
        self,
        records: Sequence[CohortSubmissionRecord],
        cohort_flags: Sequence[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        cluster_membership: Dict[str, int] = defaultdict(int)
        pair_similarity: Dict[str, float] = defaultdict(float)
        for flag in cohort_flags:
            if flag.get('type') == 'intra_cohort_cluster':
                for member in str(flag.get('members', '')).split(','):
                    if member:
                        cluster_membership[member] += 1
            elif flag.get('type') == 'intra_cohort_similarity':
                a, b = str(flag.get('submission_a', '')), str(flag.get('submission_b', ''))
                sim = max(float(flag.get('text_similarity', 0.0) or 0.0), float(flag.get('code_similarity', 0.0) or 0.0))
                pair_similarity[a] = max(pair_similarity[a], sim)
                pair_similarity[b] = max(pair_similarity[b], sim)

        queue: List[Dict[str, Any]] = []
        for rec in records:
            for rb in rec.grading_result.review_bundles:
                priority_score = int(rb.get('priority_score', 0))
                if cluster_membership.get(rec.submission_id):
                    priority_score += 15
                priority_score += int(pair_similarity.get(rec.submission_id, 0.0) * 20)
                queue.append({
                    'submission_id': rec.submission_id,
                    'student_id': rec.student_id,
                    'subject_id': rec.subject_id,
                    'criterion_id': rb.get('criterion_id'),
                    'priority': self._priority_label(priority_score),
                    'priority_score': priority_score,
                    'reason': rb.get('reason', ''),
                    'suggested_action': rb.get('suggested_action', 'manual_review'),
                    'cluster_member': bool(cluster_membership.get(rec.submission_id)),
                    'similarity_boost': round(pair_similarity.get(rec.submission_id, 0.0), 3),
                })
        return sorted(queue, key=lambda x: x['priority_score'], reverse=True)

    @staticmethod
    def _priority_label(score: int) -> str:
        if score >= 90:
            return 'critical'
        if score >= 70:
            return 'high'
        if score >= 45:
            return 'medium'
        return 'low'

    @staticmethod
    def _review_priority_counts(queue: Sequence[Dict[str, Any]]) -> Dict[str, int]:
        counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        for item in queue:
            pr = str(item.get('priority', 'low'))
            counts[pr] = counts.get(pr, 0) + 1
        return counts

    def _find_anomalies(self, records: Sequence[CohortSubmissionRecord]) -> List[Dict[str, Any]]:
        if len(records) < 2:
            return []
        scores = [r.grading_result.final_score for r in records]
        score_mean = mean(scores)
        score_sd = pstdev(scores) or 1e-9
        anomalies: List[Dict[str, Any]] = []
        for rec in records:
            z = (rec.grading_result.final_score - score_mean) / score_sd
            conf = self._avg_conf(rec.grading_result)
            if abs(z) >= 1.8 or conf < 0.35 or len(rec.grading_result.review_bundles) >= 3:
                anomalies.append({
                    'submission_id': rec.submission_id,
                    'student_id': rec.student_id,
                    'subject_id': rec.subject_id,
                    'score': rec.grading_result.final_score,
                    'score_z': round(z, 3),
                    'average_confidence': round(conf, 3),
                    'review_bundle_count': len(rec.grading_result.review_bundles),
                })
        anomalies.sort(key=lambda a: (abs(a['score_z']), -a['review_bundle_count'], -a['score']), reverse=True)
        return anomalies
