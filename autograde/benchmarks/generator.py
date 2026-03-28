from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from random import Random
from typing import Callable

from autograde.utils import sample_data


@dataclass(slots=True)
class BenchmarkCase:
    case_id: str
    subject_id: str
    template_id: str
    submission_path: str
    variant: str
    expected_min_score: float
    expected_max_score: float
    expected_review: bool
    expected_statuses: list[str] = field(default_factory=list)
    notes: str = ''


class SyntheticBenchmarkGenerator:
    def __init__(self, seed: int = 7) -> None:
        self.rng = Random(seed)

    def generate_suite(self, root: str, cases_per_subject: int = 5) -> list[BenchmarkCase]:
        base = Path(root)
        base.mkdir(parents=True, exist_ok=True)
        cases: list[BenchmarkCase] = []
        for subject_id in ('programming', 'humanities', 'engineering', 'lab_science', 'mathematics'):
            for idx in range(cases_per_subject):
                cases.append(self._generate_case(subject_id, idx, base))
        return cases

    def _generate_case(self, subject_id: str, idx: int, base: Path) -> BenchmarkCase:
        if subject_id == 'programming':
            return self._programming_case(idx, base)
        if subject_id == 'humanities':
            return self._humanities_case(idx, base)
        if subject_id == 'engineering':
            return self._engineering_case(idx, base)
        if subject_id == 'lab_science':
            return self._lab_science_case(idx, base)
        if subject_id == 'mathematics':
            return self._mathematics_case(idx, base)
        raise ValueError(subject_id)

    def _prep_dir(self, root: Path) -> None:
        if root.exists():
            for path in sorted(root.rglob('*'), reverse=True):
                if path.is_file():
                    path.unlink()
                else:
                    path.rmdir()
        root.mkdir(parents=True, exist_ok=True)

    def _programming_case(self, idx: int, base: Path) -> BenchmarkCase:
        variants = ['clean', 'probeable_broken', 'contradictory', 'missing_results']
        variant = variants[idx % len(variants)]
        root = base / f'programming_{idx:03d}_{variant}'
        self._prep_dir(root)
        if variant == 'clean':
            sample_data.build_sample_submission(str(root))
            return BenchmarkCase(root.name, 'programming', 'programming_project', str(root), variant, 55, 100, False)
        if variant == 'probeable_broken':
            sample_data.build_hardcoded_but_probeable_submission(str(root))
            return BenchmarkCase(root.name, 'programming', 'programming_project', str(root), variant, 55, 95, False)
        if variant == 'contradictory':
            sample_data.build_contradictory_submission(str(root))
            return BenchmarkCase(root.name, 'programming', 'programming_project', str(root), variant, 0, 70, True, ['escalated'])
        sample_data.build_sample_submission(str(root))
        (root / 'results.csv').unlink(missing_ok=True)
        report = (root / 'report.txt').read_text(encoding='utf-8')
        report += '\n\nThe benchmark comparison was omitted, and results are still preliminary.\n'
        (root / 'report.txt').write_text(report, encoding='utf-8')
        return BenchmarkCase(root.name, 'programming', 'programming_project', str(root), variant, 20, 80, False, ['partially_graded'])

    def _humanities_case(self, idx: int, base: Path) -> BenchmarkCase:
        variants = ['essay_strong', 'short_correct', 'thin_answer', 'creative_long']
        variant = variants[idx % len(variants)]
        root = base / f'humanities_{idx:03d}_{variant}'
        self._prep_dir(root)
        if variant == 'essay_strong':
            sample_data.build_humanities_essay_submission(str(root))
            return BenchmarkCase(root.name, 'humanities', 'essay', str(root), variant, 55, 100, False)
        if variant == 'short_correct':
            sample_data.build_humanities_short_answer_submission(str(root))
            return BenchmarkCase(root.name, 'humanities', 'short_answer', str(root), variant, 35, 95, False)
        if variant == 'thin_answer':
            (root / 'response.txt').write_text('Institutions matter because they shape behavior.', encoding='utf-8')
            return BenchmarkCase(root.name, 'humanities', 'short_answer', str(root), variant, 0, 65, False, ['partially_graded'])
        sample_data.build_humanities_essay_submission(str(root))
        essay = (root / 'essay.txt').read_text(encoding='utf-8')
        essay += '\n\nA different but still valid interpretation is that institutional rules act mainly as boundary conditions for interpretation rather than direct causes.\n'
        (root / 'essay.txt').write_text(essay, encoding='utf-8')
        return BenchmarkCase(root.name, 'humanities', 'essay', str(root), variant, 45, 100, False)

    def _engineering_case(self, idx: int, base: Path) -> BenchmarkCase:
        variants = ['known_family', 'plausible_unknown', 'missing_simulation', 'weak_explanation']
        variant = variants[idx % len(variants)]
        root = base / f'engineering_{idx:03d}_{variant}'
        self._prep_dir(root)
        if variant == 'known_family':
            sample_data.build_engineering_circuit_submission(str(root))
            return BenchmarkCase(root.name, 'engineering', 'circuit_design', str(root), variant, 50, 100, False)
        if variant == 'plausible_unknown':
            sample_data.build_engineering_plausible_unknown_submission(str(root))
            return BenchmarkCase(root.name, 'engineering', 'circuit_design', str(root), variant, 20, 90, True, ['escalated', 'partially_graded'])
        if variant == 'missing_simulation':
            sample_data.build_engineering_circuit_submission(str(root))
            (root / 'simulation.csv').unlink(missing_ok=True)
            return BenchmarkCase(root.name, 'engineering', 'circuit_design', str(root), variant, 10, 80, False, ['partially_graded'])
        sample_data.build_engineering_circuit_submission(str(root))
        (root / 'report.txt').write_text('Title: Minimal circuit note\nThis design likely works.', encoding='utf-8')
        return BenchmarkCase(root.name, 'engineering', 'circuit_design', str(root), variant, 10, 75, False, ['partially_graded'])

    def _lab_science_case(self, idx: int, base: Path) -> BenchmarkCase:
        variants = ['solid_lab', 'no_limitations', 'results_only', 'weak_method']
        variant = variants[idx % len(variants)]
        root = base / f'lab_{idx:03d}_{variant}'
        self._prep_dir(root)
        sample_data.build_lab_science_submission(str(root))
        if variant == 'solid_lab':
            return BenchmarkCase(root.name, 'lab_science', 'lab_report', str(root), variant, 45, 100, False)
        if variant == 'no_limitations':
            text = (root / 'report.txt').read_text(encoding='utf-8').replace(' A limitation is that measurement uncertainty and timing error may affect the precise optimum.', '')
            (root / 'report.txt').write_text(text, encoding='utf-8')
            return BenchmarkCase(root.name, 'lab_science', 'lab_report', str(root), variant, 25, 90, False, ['partially_graded'])
        if variant == 'results_only':
            (root / 'report.txt').write_text('Results: activity increased and then declined with temperature. Interpretation is omitted.', encoding='utf-8')
            return BenchmarkCase(root.name, 'lab_science', 'lab_report', str(root), variant, 5, 65, False, ['partially_graded'])
        (root / 'report.txt').write_text('Method: We tested enzyme activity. Results are shown in the table.', encoding='utf-8')
        return BenchmarkCase(root.name, 'lab_science', 'lab_report', str(root), variant, 5, 70, False, ['partially_graded'])

    def _mathematics_case(self, idx: int, base: Path) -> BenchmarkCase:
        variants = ['clean_proof', 'missing_step', 'conclusion_only', 'alt_valid']
        variant = variants[idx % len(variants)]
        root = base / f'mathematics_{idx:03d}_{variant}'
        self._prep_dir(root)
        if variant == 'clean_proof':
            sample_data.build_mathematics_proof_submission(str(root))
            return BenchmarkCase(root.name, 'mathematics', 'proof', str(root), variant, 40, 100, False)
        if variant == 'missing_step':
            sample_data.build_mathematics_proof_submission(str(root))
            text = (root / 'solution.txt').read_text(encoding='utf-8').replace('Because m+n is an integer, the quantity a+b is divisible by 2. ', '')
            (root / 'solution.txt').write_text(text, encoding='utf-8')
            return BenchmarkCase(root.name, 'mathematics', 'proof', str(root), variant, 15, 80, False, ['partially_graded'])
        if variant == 'conclusion_only':
            (root / 'solution.txt').write_text('The sum of two even integers is even. Therefore the statement is true.', encoding='utf-8')
            return BenchmarkCase(root.name, 'mathematics', 'proof', str(root), variant, 0, 50, False, ['partially_graded'])
        (root / 'solution.txt').write_text(
            'Let a=2m and b=2n. Then a+b = 2m+2n = 2(m+n). Since m+n is an integer, the sum is even. Thus the claim follows.',
            encoding='utf-8')
        return BenchmarkCase(root.name, 'mathematics', 'proof', str(root), variant, 35, 100, False)
