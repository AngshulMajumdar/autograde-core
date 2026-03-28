from __future__ import annotations

from datetime import datetime

from autograde.integrity.checks import ExternalSource, IntegrityEngine
from autograde.models import Artifact, EvidenceObject, Location, Submission


def make_submission(submission_id: str, student_id: str, text: str = '', code: str = '') -> Submission:
    sub = Submission(submission_id=submission_id, assignment_id='A1', student_id=student_id, submitted_at=datetime.utcnow())
    if text:
        art = Artifact(
            artifact_id=f'art_{submission_id}_r', submission_id=submission_id, file_name='report.txt', artifact_type='report',
            mime_type='text/plain', storage_path='report.txt', checksum='x', size_bytes=len(text), parse_status='parsed'
        )
        sub.add_artifact(art)
        sub.add_evidence(EvidenceObject(
            evidence_id=f'ev_{submission_id}_t', submission_id=submission_id, artifact_id=art.artifact_id,
            modality='text', subtype='body', content=text, location=Location(file='report.txt'), extractor_id='unit',
        ))
    if code:
        art = Artifact(
            artifact_id=f'art_{submission_id}_c', submission_id=submission_id, file_name='main.py', artifact_type='source_code',
            mime_type='text/x-python', storage_path='main.py', checksum='y', size_bytes=len(code), parse_status='parsed'
        )
        sub.add_artifact(art)
        sub.add_evidence(EvidenceObject(
            evidence_id=f'ev_{submission_id}_c', submission_id=submission_id, artifact_id=art.artifact_id,
            modality='code', subtype='function', content=code, location=Location(file='main.py'), extractor_id='unit',
        ))
    return sub


def run_demo():
    engine = IntegrityEngine()

    cited_text = (
        'According to Goodfellow et al. (2016), deep neural networks can approximate complex functions. '
        'In this paper we discuss why representation depth matters for learning.'
    )
    cited_source = ExternalSource(
        source_id='src_book',
        text='Deep neural networks can approximate complex functions and representation depth matters for learning.',
        metadata={'source_type': 'book'}
    )
    cited_sub = make_submission('sub_cited', 's1', text=cited_text)
    cited_flags = engine.check_external_sources(cited_sub, [cited_source])
    assert not any(f['type'] == 'external_text_similarity' for f in cited_flags), cited_flags

    template_code = '''
import json

def load_data(path):
    with open(path) as f:
        return json.load(f)
'''
    template_source = ExternalSource(
        source_id='starter_code',
        text=template_code,
        metadata={'is_template': True, 'source_type': 'starter_code'}
    )
    code_sub = make_submission('sub_code', 's2', code=template_code)
    code_flags = engine.check_external_sources(code_sub, [template_source])
    assert not any(f['type'] == 'external_code_similarity' for f in code_flags), code_flags

    sub_a = make_submission('sub_a', 'sa', code='''
def bfs(graph, start):
    visited = set([start])
    queue = [start]
    order = []
    while queue:
        node = queue.pop(0)
        order.append(node)
        for nxt in graph.get(node, []):
            if nxt not in visited:
                visited.add(nxt)
                queue.append(nxt)
    return order
''')
    sub_b = make_submission('sub_b', 'sb', code='''
def bfs(adj, src):
    seen = {src}
    q = [src]
    out = []
    while q:
        u = q.pop(0)
        out.append(u)
        for v in adj.get(u, []):
            if v not in seen:
                seen.add(v)
                q.append(v)
    return out
''')
    cohort_flags = engine.check_intra_cohort_similarity([sub_a, sub_b])
    assert not any(f['type'] == 'intra_cohort_similarity' for f in cohort_flags), cohort_flags

    print({'cited_text_flags': cited_flags, 'template_code_flags': code_flags, 'cohort_flags': cohort_flags})


if __name__ == '__main__':
    run_demo()
