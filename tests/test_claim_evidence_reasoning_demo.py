from __future__ import annotations

from pathlib import Path

from autograde.executor import GradingExecutor
from autograde.ingestion import SubmissionIngestionPipeline
from autograde.rubric import Criterion, Rubric, ScoringPolicy
from autograde.utils.sample_data import build_contradictory_submission


def _reset_dir(root: Path) -> None:
    if root.exists():
        for path in sorted(root.rglob('*'), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()


def build_rubric() -> Rubric:
    return Rubric(
        assignment_id='CS999_CLAIM',
        assignment_title='Claim Evidence Reasoning Demo',
        required_artifacts=['report', 'source_code', 'spreadsheet'],
        criteria=[
            Criterion(
                criterion_id='C1',
                name='Claim credibility',
                description='Check whether reported claims are supported by implementation and results.',
                max_score=20,
                weight=1.0,
                required_modalities=['text', 'code', 'table'],
                evaluation_dimensions=['consistency'],
                artifact_scope=['report', 'source_code', 'spreadsheet'],
                scoring_policy=ScoringPolicy(mode='weighted_average'),
            )
        ],
        normalize_to=100.0,
    )


def main() -> None:
    root = Path('/mnt/data/v24/tests/runtime_claim_evidence_submission')
    _reset_dir(root)
    build_contradictory_submission(str(root))

    submission = SubmissionIngestionPipeline().ingest_submission(
        assignment_id='CS999_CLAIM',
        submission_path=str(root),
        submission_id='sub_claim_ev_001',
        student_id='2021CS9999',
    )

    result = GradingExecutor().grade_submission(submission, build_rubric())
    c1 = result.criterion_results[0]

    assert c1.claim_evidence_results, 'Expected claim-evidence reasoning output.'
    statuses = {row['support_status'] for row in c1.claim_evidence_results}
    assert 'contradicted' in statuses or 'unsupported' in statuses
    assert c1.manual_review_required
    assert c1.score < c1.max_score
    print({'score': c1.score, 'statuses': sorted(statuses), 'review': c1.manual_review_required})


if __name__ == '__main__':
    main()
