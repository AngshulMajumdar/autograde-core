from __future__ import annotations

import json
from pathlib import Path

from autograde.executor.claims import ClaimExtractor
from autograde.models import EvidenceObject
from scripts.run_course_simulation import simulate


def test_llm_first_claim_extractor_still_falls_back_offline() -> None:
    ev = EvidenceObject(
        evidence_id='ev1', submission_id='sub1', artifact_id='art1', modality='text', subtype='body',
        content='We implemented Dijkstra algorithm and achieved accuracy 98%.', structured_content={}, location={}, confidence=1.0,
    )
    claims = ClaimExtractor(use_llm=True, heuristic_fallback=True).extract([ev])
    assert claims
    assert any(c.subject == 'algorithm' for c in claims)
    assert any(c.source in {'llm', 'heuristic'} for c in claims)


def test_course_simulation_outputs_files(tmp_path: Path) -> None:
    summary = simulate(str(tmp_path), submissions=25, seed=3)
    assert summary['generated_cases'] >= 25
    assert (tmp_path / 'course_simulation_summary.json').exists()
    assert (tmp_path / 'course_simulation_report.txt').exists()
    data = json.loads((tmp_path / 'course_simulation_summary.json').read_text(encoding='utf-8'))
    assert 'subjects' in data and data['subjects']
