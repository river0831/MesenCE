"""Replay recorded visible-translation snapshots into a companion renderer."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path
from typing import Any, Callable, Iterable, TextIO


def load_snapshots(path: Path) -> list[dict[str, Any]]:
    snapshots = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            snapshot = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid JSON at line {line_number}: {error}") from error
        if not isinstance(snapshot, dict) or (
            snapshot.get("mode") != "visible-translation-snapshot"
            or not isinstance(snapshot.get("frame"), int)
            or not isinstance(snapshot.get("items"), list)
        ):
            raise ValueError(f"invalid translation snapshot at line {line_number}")
        snapshots.append(snapshot)
    if not snapshots:
        raise ValueError("snapshot trace is empty")
    return snapshots


def replay_snapshots(
    snapshots: Iterable[dict[str, Any]],
    output: TextIO,
    *,
    fps: float = 60.0,
    speed: float = 1.0,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    if fps <= 0 or speed <= 0:
        raise ValueError("fps and speed must be positive")
    previous_frame: int | None = None
    for snapshot in snapshots:
        frame = snapshot["frame"]
        if previous_frame is not None and frame > previous_frame:
            sleep((frame - previous_frame) / fps / speed)
        output.write(json.dumps(snapshot, ensure_ascii=False) + "\n")
        output.flush()
        previous_frame = frame


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace", required=True, type=Path)
    parser.add_argument("--subtitle-companion", required=True, type=Path)
    parser.add_argument("--fps", type=float, default=60.0)
    parser.add_argument("--speed", type=float, default=1.0)
    args = parser.parse_args()
    snapshots = load_snapshots(args.trace)
    with subprocess.Popen(
        ["/usr/bin/python3", str(args.subtitle_companion)],
        stdin=subprocess.PIPE,
        text=True,
    ) as companion:
        assert companion.stdin is not None
        replay_snapshots(
            snapshots, companion.stdin, fps=args.fps, speed=args.speed
        )
        companion.stdin.close()
        raise SystemExit(companion.wait())


if __name__ == "__main__":
    main()
