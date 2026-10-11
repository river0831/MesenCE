"""Replay JSONL ROM-read traces through the resolver and debug renderer."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .database import load_database
from .display import DebugRenderer
from .events import InputEvent, RomReadEvent
from .resolver import TextResolver


def replay(database_path: Path, trace_path: Path) -> list[dict]:
    database = load_database(database_path)
    resolver = TextResolver(database)
    renderer = DebugRenderer(database)
    commands: list[dict] = []
    for line_number, line in enumerate(trace_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        item = json.loads(line)
        if item.get("type") == "hide":
            text_events = resolver.hide(int(item["frame"]))
        elif item.get("type") == "input":
            text_events = resolver.consume(InputEvent(
                type="input",
                frame=int(item["frame"]),
                buttons=int(item["buttons"]),
            ))
        elif item.get("type") == "rom-read":
            text_events = resolver.consume(RomReadEvent(
                type="rom-read",
                frame=int(item["frame"]),
                cpu_address=int(item["cpuAddress"]),
                prg_offset=int(item["prgOffset"]),
                value=int(item["value"]),
                cpu_pc=int(item["cpuPc"]),
            ))
        else:
            raise ValueError(f"unsupported trace event on line {line_number}")
        commands.extend(asdict(renderer.consume(event)) for event in text_events)
    return commands


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("database", type=Path)
    parser.add_argument("trace", type=Path)
    args = parser.parse_args()
    for command in replay(args.database, args.trace):
        print(json.dumps(command, ensure_ascii=False))


if __name__ == "__main__":
    main()
