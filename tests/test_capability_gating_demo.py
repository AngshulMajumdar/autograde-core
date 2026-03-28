from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

from autograde.executor import GradingExecutor
from autograde.ingestion import SubmissionIngestionPipeline
from autograde.rubric import Criterion, Rubric, ScoringPolicy


def _reset_dir(root: Path) -> None:
    if root.exists():
        for path in sorted(root.rglob('*'), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()


def _write_wav(path: Path, seconds: float = 0.1, sample_rate: int = 8000) -> None:
    n = int(seconds * sample_rate)
    with wave.open(str(path), 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        frames = []
        for i in range(n):
            v = int(12000 * math.sin(2 * math.pi * 440 * i / sample_rate))
            frames.append(struct.pack('<h', v))
        wf.writeframes(b''.join(frames))


def main() -> None:
    root = Path('/mnt/data/work_v19/tests/runtime_capability_submission')
    _reset_dir(root)
    root.mkdir(parents=True, exist_ok=True)
    (root / 'answer.txt').write_text('This is a plain text answer about algorithms.', encoding='utf-8')
    _write_wav(root / 'oral.wav')
    (root / 'oral.txt').write_text('Spoken explanation transcript.', encoding='utf-8')

    pipeline = SubmissionIngestionPipeline()
    submission = pipeline.ingest_submission(
        assignment_id='CAPABILITY_DEMO',
        submission_path=str(root),
        submission_id='sub_cap_001',
        student_id='2021CAP001',
    )

    rubric = Rubric(
        assignment_id='CAPABILITY_DEMO',
        assignment_title='Capability Gating Demo',
        required_artifacts=['text'],
        criteria=[
            Criterion(
                criterion_id='U1',
                name='Unsupported CAD Criterion',
                description='Should route to manual review because CAD is unsupported.',
                max_score=10.0,
                weight=0.5,
                required_modalities=['cad'],
                evaluation_dimensions=['completeness'],
                scoring_policy=ScoringPolicy(mode='weighted_average'),
            ),
            Criterion(
                criterion_id='A1',
                name='Audio Reflection',
                description='Should be partially graded because audio is only partially supported.',
                max_score=10.0,
                weight=0.5,
                required_modalities=['audio'],
                artifact_scope=['audio'],
                evaluation_dimensions=['completeness'],
                scoring_policy=ScoringPolicy(mode='weighted_average'),
            ),
        ],
    )

    result = GradingExecutor().grade_submission(submission, rubric)
    print('Final score:', result.final_score)
    print('Review bundles:', result.review_bundles)
    for cr in result.criterion_results:
        print(cr.criterion_id, cr.status, cr.capability_status, cr.support_status, cr.score)

    u1 = next(cr for cr in result.criterion_results if cr.criterion_id == 'U1')
    a1 = next(cr for cr in result.criterion_results if cr.criterion_id == 'A1')

    assert u1.status == 'unsupported_needs_review'
    assert u1.capability_status == 'unsupported'
    assert u1.manual_review_required is True

    assert a1.status == 'partially_graded'
    assert a1.capability_status == 'supported'
    assert a1.support_status == 'partial'
    assert a1.score > 0

    bundle_ids = {rb['criterion_id'] for rb in result.review_bundles}
    assert {'U1', 'A1'}.issubset(bundle_ids)


if __name__ == '__main__':
    main()
