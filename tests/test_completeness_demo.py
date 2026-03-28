from __future__ import annotations

import tempfile

from autograde.ingestion.pipeline import SubmissionIngestionPipeline
from autograde.utils.sample_data import build_multimodal_submission


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        build_multimodal_submission(tmp)
        pipeline = SubmissionIngestionPipeline()
        submission = pipeline.ingest_submission('COMPLETE', tmp, 'sub_complete', 'student_complete')

        subtypes = {e.subtype for e in submission.evidence}
        modalities = {e.modality for e in submission.evidence}

        assert 'document_structure' in subtypes
        assert 'presentation_structure' in subtypes
        assert 'audio_metadata' in subtypes
        assert 'video_metadata' in subtypes
        assert 'xlsx_dataset' in subtypes
        assert 'json_dataset' in subtypes
        assert 'audio' in modalities
        assert 'video' in modalities
        assert 'dataset' in modalities

        print({
            'artifact_inventory': submission.manifest.artifact_inventory,
            'evidence_inventory': submission.manifest.evidence_inventory,
            'subtypes': sorted(list(subtypes))[:20],
        })


if __name__ == '__main__':
    main()
