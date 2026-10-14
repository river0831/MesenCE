"""Promote exact live catalog discoveries into a validated dialogue catalog."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .catalog_validation import apply_runtime_discoveries


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--discoveries", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    events = [
        json.loads(line) for line in args.discoveries.read_text(
            encoding="utf-8"
        ).splitlines() if line.strip()
    ]
    result = apply_runtime_discoveries(
        catalog, events, trace=str(args.discoveries)
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result["discoveryValidationSummary"], indent=2))


if __name__ == "__main__":
    main()
