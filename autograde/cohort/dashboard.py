from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .analyzer import CohortAnalysis


class CohortDashboardWriter:
    def write(self, analysis: CohortAnalysis, output_dir: str) -> dict[str, str]:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        queue_json = out / 'review_queue.json'
        queue_csv = out / 'review_priority_table.csv'
        summary_json = out / 'cohort_summary.json'

        queue_json.write_text(json.dumps(analysis.prioritized_review_queue, indent=2), encoding='utf-8')
        summary_payload: dict[str, Any] = {
            'total_submissions': analysis.total_submissions,
            'average_score': analysis.average_score,
            'median_score': analysis.median_score,
            'score_std': analysis.score_std,
            'average_confidence': analysis.average_confidence,
            'review_rate': analysis.review_rate,
            'priority_review_counts': analysis.priority_review_counts,
            'subject_breakdown': analysis.subject_breakdown,
            'plagiarism_clusters': analysis.plagiarism_clusters,
            'anomalous_submissions': analysis.anomalous_submissions,
        }
        summary_json.write_text(json.dumps(summary_payload, indent=2), encoding='utf-8')

        with queue_csv.open('w', newline='', encoding='utf-8') as f:
            fieldnames = [
                'submission_id', 'student_id', 'subject_id', 'criterion_id', 'priority',
                'priority_score', 'suggested_action', 'cluster_member', 'similarity_boost', 'reason'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in analysis.prioritized_review_queue:
                writer.writerow({k: row.get(k, '') for k in fieldnames})

        return {
            'review_queue_json': str(queue_json),
            'review_priority_csv': str(queue_csv),
            'cohort_summary_json': str(summary_json),
        }
