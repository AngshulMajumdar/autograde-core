from __future__ import annotations

import json
from pathlib import Path

from autograde.capabilities import CAPABILITY_REGISTRY, describe_capability


def run_audit() -> dict:
    summary = {
        "capabilities": {k: describe_capability(v) for k, v in CAPABILITY_REGISTRY.items()},
        "strong": sorted(k for k, v in CAPABILITY_REGISTRY.items() if describe_capability(v) == "strong"),
        "partial": sorted(k for k, v in CAPABILITY_REGISTRY.items() if describe_capability(v) == "partial"),
        "weak": sorted(k for k, v in CAPABILITY_REGISTRY.items() if describe_capability(v) == "weak"),
        "unsupported": sorted(k for k, v in CAPABILITY_REGISTRY.items() if describe_capability(v) == "unsupported"),
    }
    return summary


def main() -> None:
    summary = run_audit()
    print(json.dumps(summary, indent=2, sort_keys=True))
    Path("system_audit.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()
