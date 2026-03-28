from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_llm_live_smoke_script_runs_with_mock() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "test_llm_live.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--allow-mock", "--json"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(proc.stdout)
    assert payload["provider_class"] in {"MockLLMProvider", "OllamaProvider", "OpenRouterProvider", "OpenAIChatProvider"}
    assert len(payload["results"]) >= 3
    assert all("score" in item and "confidence" in item for item in payload["results"])
