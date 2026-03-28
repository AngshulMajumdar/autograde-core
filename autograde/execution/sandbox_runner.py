from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Any, Dict


class SandboxRunner:
    """Small subprocess sandbox for unit probes.

    This is intentionally minimal in v1: timeout-limited, isolated Python process,
    and execution only of generated probe scripts.
    """

    def __init__(self, timeout_seconds: int = 3) -> None:
        self.timeout_seconds = timeout_seconds

    def run_probe(self, module_path: str, function_name: str, probe_kind: str) -> Dict[str, Any]:
        script = self._build_probe_script(module_path, function_name, probe_kind)
        with tempfile.TemporaryDirectory(prefix="ag_probe_") as tmpdir:
            script_path = Path(tmpdir) / "probe.py"
            script_path.write_text(script, encoding="utf-8")
            try:
                proc = subprocess.run(
                    [sys.executable, "-I", str(script_path)],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                    cwd=tmpdir,
                    env={},
                )
            except subprocess.TimeoutExpired:
                return {
                    "status": "timeout",
                    "tests_run": 0,
                    "tests_passed": 0,
                    "rationale": f"Unit probes timed out for {function_name}.",
                }

            stdout = (proc.stdout or "").strip()
            if not stdout:
                return {
                    "status": "error",
                    "tests_run": 0,
                    "tests_passed": 0,
                    "rationale": (proc.stderr or "Probe produced no output.").strip()[:300],
                }
            try:
                return json.loads(stdout)
            except json.JSONDecodeError:
                return {
                    "status": "error",
                    "tests_run": 0,
                    "tests_passed": 0,
                    "rationale": stdout[:300],
                }

    def _build_probe_script(self, module_path: str, function_name: str, probe_kind: str) -> str:
        return textwrap.dedent(
            f"""
            import importlib.util, json, traceback

            MODULE_PATH = {module_path!r}
            FUNCTION_NAME = {function_name!r}
            PROBE_KIND = {probe_kind!r}

            def load_function():
                spec = importlib.util.spec_from_file_location('student_module', MODULE_PATH)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return getattr(module, FUNCTION_NAME)

            def run_dijkstra(fn):
                tests = []
                graph = {{
                    'A': [('B', 1), ('C', 4)],
                    'B': [('C', 2), ('D', 6)],
                    'C': [('D', 3)],
                    'D': []
                }}
                out = fn(graph, 'A')
                ok = isinstance(out, dict) and out.get('A') == 0 and out.get('B') == 1 and out.get('C') == 3 and out.get('D') == 6
                tests.append(('shortest_path_small_graph', ok, str(out)[:150]))

                graph2 = {{'S': [('T', 5)], 'T': [], 'U': []}}
                out2 = fn(graph2, 'S')
                ok2 = isinstance(out2, dict) and out2.get('S') == 0 and out2.get('T') == 5 and ('U' in out2)
                tests.append(('disconnected_node_retained', ok2, str(out2)[:150]))
                return tests

            def run_bfs(fn):
                tests = []
                graph = {{'A': ['B', 'C'], 'B': ['D'], 'C': [], 'D': []}}
                out = fn(graph, 'A')
                ok = isinstance(out, (list, tuple, set, dict))
                tests.append(('bfs_basic_callable', ok, str(out)[:150]))
                return tests

            def main():
                try:
                    fn = load_function()
                    if PROBE_KIND == 'dijkstra':
                        tests = run_dijkstra(fn)
                    elif PROBE_KIND == 'bfs':
                        tests = run_bfs(fn)
                    else:
                        tests = [('callable_loaded', callable(fn), FUNCTION_NAME)]
                    tests_run = len(tests)
                    tests_passed = sum(1 for _, ok, _ in tests if ok)
                    payload = {{
                        'status': 'ok',
                        'probe_kind': PROBE_KIND,
                        'function_name': FUNCTION_NAME,
                        'tests_run': tests_run,
                        'tests_passed': tests_passed,
                        'test_details': [{{'name': name, 'passed': ok, 'detail': detail}} for name, ok, detail in tests],
                        'rationale': f'Ran {{tests_run}} unit probe(s) for {{FUNCTION_NAME}} and passed {{tests_passed}}.',
                    }}
                except Exception as exc:
                    payload = {{
                        'status': 'exception',
                        'probe_kind': PROBE_KIND,
                        'function_name': FUNCTION_NAME,
                        'tests_run': 0,
                        'tests_passed': 0,
                        'rationale': f'Probe execution failed: {{type(exc).__name__}}: {{exc}}',
                        'traceback': traceback.format_exc()[:1200],
                    }}
                print(json.dumps(payload))

            if __name__ == '__main__':
                main()
            """
        )
