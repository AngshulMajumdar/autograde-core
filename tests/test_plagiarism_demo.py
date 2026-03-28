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


def _build_submission(root: Path, code_name: str = "solve") -> None:
    (root / 'report.txt').write_text(
        "We implemented Dijkstra's algorithm using an adjacency-list graph representation. "
        "The algorithm maintains a priority queue and achieved accuracy 98% on the benchmark.\n\n"
        "The implementation uses a priority queue to repeatedly select the node with minimum distance. "
        "This description is intentionally close to a known source for integrity testing.",
        encoding='utf-8',
    )
    (root / 'main.py').write_text(
        f"def relax_candidate(dist, vertex, cand):\n"
        "    if vertex not in dist or cand < dist[vertex]:\n"
        "        dist[vertex] = cand\n"
        "        return True\n"
        "    return False\n\n"
        f"def {code_name}(graph, src):\n"
        "    dist = {src: 0}\n"
        "    frontier = [(0, src)]\n"
        "    while frontier:\n"
        "        d, u = frontier.pop(0)\n"
        "        for v, w in graph.get(u, []):\n"
        "            cand = d + w\n"
        "            if relax_candidate(dist, v, cand):\n"
        "                frontier.append((cand, v))\n"
        "    return dist\n",
        encoding='utf-8',
    )


def build_rubric() -> Rubric:
    return Rubric(
        assignment_id='CSX_A1',
        assignment_title='Integrity demo',
        required_artifacts=['report', 'source_code'],
        criteria=[
            Criterion(
                criterion_id='C1',
                name='Implementation quality',
                description='Check code quality',
                max_score=20,
                weight=1.0,
                required_modalities=['code'],
                evaluation_dimensions=['correctness'],
                artifact_scope=['source_code'],
                scoring_policy=ScoringPolicy(mode='weighted_average'),
            )
        ],
        normalize_to=100.0,
    )


def main() -> None:
    base = Path('/mnt/data/work_autograde/tests/runtime_plagiarism')
    roots = [base / 'sub1', base / 'sub2', base / 'sub3']
    for root in roots:
        _reset_dir(root)
    _build_submission(roots[0], code_name='solve')
    _build_submission(roots[1], code_name='compute')
    _build_submission(roots[2], code_name='run')

    pipeline = SubmissionIngestionPipeline()
    subs = [
        pipeline.ingest_submission('CSX_A1', str(root), f'sub_{idx+1}', f'2021CS0{idx+1}')
        for idx, root in enumerate(roots)
    ]

    executor = GradingExecutor()
    rubric = build_rubric()
    result = executor.grade_submission(
        subs[0],
        rubric,
        source_corpus=[
            ExternalSource(
                source_id='ext_ds_notes',
                text=(
                    "We implemented Dijkstra's algorithm using an adjacency-list graph representation. "
                    "The algorithm maintains a priority queue and achieved accuracy 98% on the benchmark. "
                    "The implementation uses a priority queue to repeatedly select the node with minimum distance."
                ),
            ),
            ExternalSource(
                source_id='ext_code_repo',
                text=(
                    "def relax_candidate(dist, vertex, cand):\n"
                    "    if vertex not in dist or cand < dist[vertex]:\n"
                    "        dist[vertex] = cand\n"
                    "        return True\n"
                    "    return False\n\n"
                    "def shortest_path(graph, src):\n"
                    "    dist = {src: 0}\n"
                    "    frontier = [(0, src)]\n"
                    "    while frontier:\n"
                    "        d, u = frontier.pop(0)\n"
                    "        for v, w in graph.get(u, []):\n"
                    "            cand = d + w\n"
                    "            if relax_candidate(dist, v, cand):\n"
                    "                frontier.append((cand, v))\n"
                    "    return dist\n"
                ),
            )
        ],
    )
    cohort_flags = executor.grade_cohort_similarity(subs)

    print('External flags:', result.review_flags)
    print('Cohort flags:', cohort_flags)

    assert any(flag['type'] == 'external_text_similarity' for flag in result.review_flags)
    assert any(flag['type'] == 'external_code_similarity' for flag in result.review_flags)
    assert any(flag['type'] == 'intra_cohort_similarity' for flag in cohort_flags)
    assert any(flag['type'] == 'intra_cohort_cluster' for flag in cohort_flags)


if __name__ == '__main__':
    main()
