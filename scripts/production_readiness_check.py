from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autograde.llm.client import get_default_llm_client


def main() -> int:
    client = get_default_llm_client()
    checks = {
        'llm_provider': client.provider_name,
        'llm_live': client.is_live,
        'strict_llm': os.getenv('AUTOGRADE_STRICT_LLM', '0'),
        'allow_mock_llm': os.getenv('AUTOGRADE_ALLOW_MOCK_LLM', '1'),
        'placeholder_audit_script': (ROOT / 'scripts' / 'placeholder_audit.py').exists(),
        'pyproject_present': (ROOT / 'pyproject.toml').exists(),
        'api_present': (ROOT / 'autograde' / 'api' / 'app.py').exists(),
    }
    checks['ready_for_live_llm'] = bool(checks['llm_live'])
    checks['warning'] = None if checks['llm_live'] else 'LLM path is using MockLLMProvider. Set AUTOGRADE_STRICT_LLM=1 to block mock execution.'
    print(json.dumps(checks, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
