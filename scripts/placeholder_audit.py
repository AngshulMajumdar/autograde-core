
from __future__ import annotations
import os, re, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {'tests', '__pycache__', '.pytest_cache'}
PATTERNS = {
    'todo': re.compile(r'\bTODO\b', re.I),
    'fixme': re.compile(r'\bFIXME\b', re.I),
    'placeholder': re.compile(r'\bplaceholder\b', re.I),
    'mock': re.compile(r'\bMock[A-Za-z_]*\b'),
    'heuristic': re.compile(r'\bheuristic\w*\b', re.I),
    'notimplemented': re.compile(r'NotImplemented'),
}
IGNORE_FILES = {'autograde/evaluators/base.py', 'autograde/extractors/base.py'}

def main() -> int:
    findings = []
    for path in ROOT.rglob('*.py'):
        rel = path.relative_to(ROOT).as_posix()
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        txt = path.read_text(encoding='utf-8', errors='ignore')
        for key, pat in PATTERNS.items():
            if rel in IGNORE_FILES and key == 'notimplemented':
                continue
            matches = list(pat.finditer(txt))
            if matches:
                findings.append({'file': rel, 'marker': key, 'count': len(matches)})
    summary = {}
    for item in findings:
        summary[item['marker']] = summary.get(item['marker'], 0) + item['count']
    print(json.dumps({'summary': summary, 'findings': findings}, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
