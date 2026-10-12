"""Capture bounded Dragon Quest runtime diagnostics as portable JSONL."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

from .live import parse_trace_payload


def build_capture_script(
    template: str, *, start_immediately: bool, frame_limit: int | None
) -> str:
    if frame_limit is not None and frame_limit <= 0:
        raise ValueError("capture frame limit must be positive")
    config = [
        f"DQ_CAPTURE_IMMEDIATELY = {'true' if start_immediately else 'false'}"
    ]
    if frame_limit is not None:
        config.append(f"DQ_CAPTURE_FRAME_LIMIT = {frame_limit}")
    return "\n".join(config) + "\n" + template


def capture(
    mesen: Path,
    script: Path,
    rom: Path,
    output: Path,
    *,
    start_immediately: bool = False,
    frame_limit: int | None = None,
) -> int:
    generated_folder: tempfile.TemporaryDirectory[str] | None = None
    runtime_script = script
    if start_immediately or frame_limit is not None:
        generated_folder = tempfile.TemporaryDirectory(prefix="nes-capture-")
        runtime_script = Path(generated_folder.name) / script.name
        runtime_script.write_text(build_capture_script(
            script.read_text(encoding="utf-8"),
            start_immediately=start_immediately,
            frame_limit=frame_limit,
        ), encoding="utf-8")
    command = [
        str(mesen),
        "--enableStdout",
        "--doNotSaveSettings",
        str(runtime_script),
        str(rom),
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    counts: Counter[str] = Counter()
    if start_immediately:
        print("Starting diagnostic capture with the game...", flush=True)
    else:
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
    if generated_folder is not None:
        generated_folder.cleanup()
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesen", required=True, type=Path)
    parser.add_argument("--script", required=True, type=Path)
    parser.add_argument("--rom", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--start-immediately", action="store_true")
    parser.add_argument("--frame-limit", type=int)
    args = parser.parse_args()
    raise SystemExit(capture(
        args.mesen, args.script, args.rom, args.output,
        start_immediately=args.start_immediately,
        frame_limit=args.frame_limit,
    ))


if __name__ == "__main__":
    main()
