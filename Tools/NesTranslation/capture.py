"""Capture bounded Dragon Quest runtime diagnostics as portable JSONL."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

from .live import parse_trace_payload


def capture(mesen: Path, script: Path, rom: Path, output: Path) -> int:
    command = [
        str(mesen),
        "--enableStdout",
        "--doNotSaveSettings",
        str(script),
        str(rom),
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    counts: Counter[str] = Counter()
    print("Waiting for the main menu to start diagnostic capture...", flush=True)
    try:
        with output.open("w", encoding="utf-8") as trace_file, subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        ) as process:
            assert process.stdout is not None
            for line in process.stdout:
                line = line.rstrip("\n")
                if line.startswith("DQTRACE_READY"):
                    print(line, flush=True)
                    continue
                item = parse_trace_payload(line)
                if item is None:
                    continue
                trace_file.write(json.dumps(item, ensure_ascii=False) + "\n")
                trace_file.flush()
                event_type = str(item["type"])
                counts[event_type] += 1
                if event_type in {"capture-start", "capture-stop"}:
                    print(json.dumps(item, ensure_ascii=False), flush=True)
            result = process.wait()
    except KeyboardInterrupt:
        print("Capture stopped by user.", file=sys.stderr)
        result = 130

    print(
        "Captured " + ", ".join(f"{key}={value}" for key, value in sorted(counts.items())),
        flush=True,
    )
    print(f"Trace: {output}", flush=True)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesen", required=True, type=Path)
    parser.add_argument("--script", required=True, type=Path)
    parser.add_argument("--rom", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    raise SystemExit(capture(args.mesen, args.script, args.rom, args.output))


if __name__ == "__main__":
    main()
