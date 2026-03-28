from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
from PIL import Image, ImageDraw

from autograde.ingestion import SubmissionIngestionPipeline


def _reset_dir(root: Path) -> None:
    if root.exists():
        for path in sorted(root.rglob('*'), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()


def build_modality_submission(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    # Plot image with OCR-readable labels.
    plt.figure()
    plt.plot([0, 1, 2], [0.45, 0.7, 0.92])
    plt.xlabel('Epoch')
    plt.ylabel('Accuracy')
    plt.title('Accuracy 92')
    plt.tight_layout()
    plt.savefig(root / 'accuracy_plot.png')
    plt.close()

    # OCR image.
    img = Image.new('RGB', (320, 90), 'white')
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), 'GAIN 10\nCUTOFF 1000', fill='black')
    img.save(root / 'annotated_scan.png')

    # SVG diagram.
    (root / 'circuit.svg').write_text(
        """
        <svg xmlns='http://www.w3.org/2000/svg' width='300' height='140'>
          <text x='10' y='20'>input</text>
          <text x='240' y='20'>output</text>
          <text x='120' y='70'>op_amp</text>
          <text x='20' y='70'>resistor</text>
          <text x='200' y='70'>capacitor</text>
          <text x='110' y='110'>feedback</text>
          <line x1='20' y1='60' x2='120' y2='60' />
          <line x1='140' y1='60' x2='240' y2='60' />
          <path d='M240,60 L240,100 L120,100' />
        </svg>
        """,
        encoding='utf-8',
    )

    # Notebook.
    nb = {
        'cells': [
            {'cell_type': 'markdown', 'metadata': {}, 'source': ['# Experiment\n', 'We analyse results.']},
            {'cell_type': 'code', 'execution_count': 1, 'metadata': {}, 'outputs': [{'output_type': 'stream', 'name': 'stdout', 'text': 'ok\n'}], 'source': ['import math\n', 'x = 1\n']},
            {'cell_type': 'code', 'execution_count': 2, 'metadata': {}, 'outputs': [], 'source': ['print(x)\n']},
        ],
        'metadata': {},
        'nbformat': 4,
        'nbformat_minor': 5,
    }
    (root / 'analysis.ipynb').write_text(json.dumps(nb), encoding='utf-8')


def main() -> None:
    root = Path('/mnt/data/work_v16/tests/runtime_modality_submission')
    _reset_dir(root)
    build_modality_submission(root)

    pipeline = SubmissionIngestionPipeline()
    submission = pipeline.ingest_submission(
        assignment_id='MODALITY_DEMO',
        submission_path=str(root),
        submission_id='sub_mod_001',
        student_id='2021XX0001',
    )

    subtypes = {(ev.modality, ev.subtype) for ev in submission.evidence}
    previews = '\n'.join([ev.preview or '' for ev in submission.evidence])
    print('Evidence inventory:', submission.manifest.evidence_inventory)
    print('Subtypes:', sorted(subtypes))
    print('Previews:', previews)

    assert ('metadata', 'notebook_flow') in subtypes
    assert ('diagram', 'topology') in subtypes
    assert ('image', 'plot') in subtypes
    assert ('text', 'ocr_text') in subtypes

    topology_ev = next(ev for ev in submission.evidence if ev.subtype == 'topology')
    assert topology_ev.structured_content['has_feedback'] is True
    assert topology_ev.structured_content['diagram_family'] in {'active_filter_family', 'op_amp_feedback_family'}

    flow_ev = next(ev for ev in submission.evidence if ev.subtype == 'notebook_flow')
    assert flow_ev.structured_content['code_cells'] == 2
    assert flow_ev.structured_content['markdown_cells'] == 1
    assert flow_ev.structured_content['execution_monotonic'] is True

    plot_ev = next(ev for ev in submission.evidence if ev.modality == 'image' and ev.subtype == 'plot')
    assert 'accuracy' in {k.lower() for k in plot_ev.structured_content['detected_metrics'].keys()} or 'accuracy' in plot_ev.structured_content['axis_tokens']


if __name__ == '__main__':
    main()
