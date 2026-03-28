from autograde.executor.claims import ClaimExtractor
from autograde.models import EvidenceObject, Location


def test_llm_claim_extractor_demo():
    ev = EvidenceObject(
        evidence_id='ev1',
        submission_id='sub1',
        artifact_id='art1',
        modality='text',
        subtype='results',
        content='We implemented Dijkstra algorithm and obtained accuracy 98% on the benchmark.',
        location=Location(file='report.txt'),
        extractor_id='unit',
    )
    extractor = ClaimExtractor(use_llm=True)
    claims = extractor.extract([ev])
    kinds = {(c.claim_type, c.subject) for c in claims}
    assert ('algorithm_claim', 'algorithm') in kinds
    assert any(c.subject == 'accuracy' for c in claims)
