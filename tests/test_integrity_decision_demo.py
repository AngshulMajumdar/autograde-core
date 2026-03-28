from __future__ import annotations

from pathlib import Path

from autograde.executor import GradingExecutor
from autograde.ingestion import SubmissionIngestionPipeline
from autograde.integrity import ExternalSource
from autograde.rubric import Criterion, Rubric, ScoringPolicy


def _reset_dir(root: Path) -> None:
    if root.exists():
        for path in sorted(root.rglob('*'), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
    root.mkdir(parents=True, exist_ok=True)


def build_submission(root: Path) -> None:
    (root / 'report.txt').write_text(
        "We implemented Dijkstra's algorithm using an adjacency-list graph representation. "
        "The algorithm maintains a priority queue and achieved accuracy 98% on the benchmark.\n\n"
        "This report text intentionally overlaps with an external source for integrity-policy testing.",
        encoding='utf-8',
    )
    (root / 'main.py').write_text(
        "def dijkstra(graph, src):\n"
        "    dist = {src: 0}\n"
        "    frontier = [(0, src)]\n"
        "    while frontier:\n"
        "        d, u = frontier.pop(0)\n"
        "        for v, w in graph.get(u, []):\n"
        "            cand = d + w\n"
        "            if v not in dist or cand < dist[v]:\n"
        "                dist[v] = cand\n"
        "                frontier.append((cand, v))\n"
        "    return dist\n",
        encoding='utf-8',
    )


def build_rubric() -> Rubric:
    return Rubric(
        assignment_id='CSX_A2',
        assignment_title='Integrity-aware grading',
        required_artifacts=['report', 'source_code'],
        criteria=[
            Criterion(
                criterion_id='C1',
                name='Report originality and clarity',
                description='Evaluate text quality while reacting to relevant text-integrity issues.',
                max_score=20,
                weight=0.5,
                required_modalities=['text'],
                evaluation_dimensions=['clarity'],
                artifact_scope=['report'],
                scoring_policy=ScoringPolicy(mode='weighted_average'),
                integrity_policy='discount_if_relevant',
                integrity_scope='text',
                integrity_severity_threshold='medium',
            ),
            Criterion(
                criterion_id='C2',
                name='Code implementation quality',
                description='Evaluate code quality without overreacting to unrelated text-integrity issues.',
                max_score=20,
                weight=0.5,
                required_modalities=['code'],
                evaluation_dimensions=['correctness'],
                artifact_scope=['source_code'],
                scoring_policy=ScoringPolicy(mode='weighted_average'),
                integrity_policy='review_only',
                integrity_scope='code',
                integrity_severity_threshold='high',
            ),
        ],
        normalize_to=100.0,
    )


def main() -> None:
    root = Path('/mnt/data/work_autograde/tests/runtime_integrity_decision')
    _reset_dir(root)
    build_submission(root)

    pipeline = SubmissionIngestionPipeline()
    sub = pipeline.ingest_submission('CSX_A2', str(root), 'sub_integrity', '2021CS9999')
    rubric = build_rubric()
    source_corpus = [
        ExternalSource(
            source_id='ext_report',
            text=(
                "We implemented Dijkstra's algorithm using an adjacency-list graph representation. "
                "The algorithm maintains a priority queue and achieved accuracy 98% on the benchmark. "
                "This report text intentionally overlaps with an external source for integrity-policy testing."
            ),
        )
    ]

    executor = GradingExecutor()
    result = executor.grade_submission(sub, rubric, source_corpus=source_corpus)
    c1 = next(c for c in result.criterion_results if c.criterion_id == 'C1')
    c2 = next(c for c in result.criterion_results if c.criterion_id == 'C2')

    print({'C1_score': c1.score, 'C1_status': c1.status, 'C1_flags': c1.flags, 'C2_score': c2.score, 'C2_status': c2.status, 'C2_flags': c2.flags})

    assert any(f.get('type') == 'external_text_similarity' for f in result.review_flags)
    assert any(f.get('type') == 'integrity_relevance' for f in c1.flags)
    assert c1.manual_review_required
    assert c1.score < c2.score, (c1.score, c2.score)
    assert not any(f.get('type') == 'integrity_relevance' for f in c2.flags)


if __name__ == '__main__':
    main()
