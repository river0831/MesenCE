"""Launch Mesen, parse DQTRACE lines, and render translations in the terminal."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from .database import load_database, validate_rom
from .display import DebugRenderer
from .events import RomReadEvent
from .resolver import TextResolver


TRACE_PREFIX = "DQTRACE "


def parse_trace_line(line: str) -> RomReadEvent | None:
    if not line.startswith(TRACE_PREFIX):
        return None
    payload = line[len(TRACE_PREFIX):].strip()
    if not payload.startswith("{"):
        return None
    value = json.loads(payload)
    if value.get("type") != "rom-read":
        return None
    return RomReadEvent(
        type="rom-read",
        frame=int(value["frame"]),
        cpu_address=int(value["cpuAddress"]),
        prg_offset=int(value["prgOffset"]),
        value=int(value["value"]),
        cpu_pc=int(value["cpuPc"]),
    )


def run_live(mesen: Path, script: Path, rom: Path, database_path: Path) -> int:
    database = load_database(database_path)
    validate_rom(database, rom)
    resolver = TextResolver(database)
    renderer = DebugRenderer(database)
    command = [
        str(mesen),
        "--enableStdout",
        "--doNotSaveSettings",
        str(script),
        str(rom),
    ]
    print("Waiting for Mesen runtime events...", flush=True)
    with subprocess.Popen(
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
            event = parse_trace_line(line)
            if event is None:
                continue
            for text_event in resolver.consume(event):
                display = renderer.consume(text_event)
                print(json.dumps({
                    "type": display.type,
                    "recordId": display.record_id,
                    "instanceId": display.instance_id,
                    "translation": display.text,
                    "frame": text_event.frame,
                    "prgOffset": text_event.evidence_prg_offset,
                }, ensure_ascii=False), flush=True)
        return process.wait()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesen", required=True, type=Path)
    parser.add_argument("--script", required=True, type=Path)
    parser.add_argument("--rom", required=True, type=Path)
    parser.add_argument("--database", required=True, type=Path)
    args = parser.parse_args()
    try:
        raise SystemExit(run_live(args.mesen, args.script, args.rom, args.database))
    except KeyboardInterrupt:
        print("Stopped.", file=sys.stderr)
        raise SystemExit(130)


if __name__ == "__main__":
    main()
