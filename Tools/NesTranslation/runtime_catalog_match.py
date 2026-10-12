"""Match runtime CHR text windows to records in a static dialogue catalog."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class RuntimeByte:
    frame: int
    selector: int | None
    ppu_address: int
    value: int


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def extract_runtime_bytes(events: Iterable[dict[str, Any]]) -> tuple[RuntimeByte, ...]:
    """Take the first byte of each overlapping eight-byte CHR staging window."""
    pending: dict[str, Any] | None = None
    result: list[RuntimeByte] = []
    for event in events:
        event_type = event.get("type")
        if event_type == "chr-text-window":
            pending = event
        elif event_type == "chr-text-byte" and pending is not None:
            # The producer always writes the first source byte to $03B0. Later
            # writes in the same window overlap and are deliberately ignored.
            if event.get("ramAddress") != 0x03B0:
                continue
            result.append(RuntimeByte(
                frame=int(event["frame"]),
                selector=(
                    int(pending["selector"])
                    if pending.get("selector") is not None
                    else None
                ),
                ppu_address=int(pending["ppuAddress"]),
                value=int(event["value"]),
            ))
            pending = None
    return tuple(result)


def match_catalog(
    runtime_bytes: tuple[RuntimeByte, ...], catalog: dict[str, Any]
) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for record in catalog.get("records", []):
        needle = bytes.fromhex(record["rawHex"])
        if not needle:
            continue
        for index in range(0, len(runtime_bytes) - len(needle) + 1):
            window = runtime_bytes[index:index + len(needle)]
            if bytes(item.value for item in window) != needle:
                continue
            # A real stream advances one PPU byte per staged window and stays
            # on one mapper selection. This rejects accidental cross-scene
            # byte matches without interpreting the mapper register itself.
            deltas = [
                window[offset].ppu_address - window[offset - 1].ppu_address
                for offset in range(1, len(window))
            ]
            if any(delta not in (0, 1) for delta in deltas):
                continue
            selectors = {item.selector for item in window}
            if len(selectors) != 1:
                continue
            hits.append({
                "recordId": record["id"],
                "runtimeStartIndex": index,
                "runtimeEndExclusive": index + len(needle),
                "frameStart": window[0].frame,
                "frameEnd": window[-1].frame,
                "selector": window[0].selector,
                "ppuStart": window[0].ppu_address,
                "ppuEndExclusive": window[-1].ppu_address + 1,
                "sourceByteCount": len(needle),
                "decoded": record["decoded"],
                "staticLikelihood": record["evidence"]["likelihood"],
                "confidence": "runtime-confirmed",
            })
    return hits


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace", required=True, type=Path)
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    runtime_bytes = extract_runtime_bytes(load_jsonl(args.trace))
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    hits = match_catalog(runtime_bytes, catalog)
    covered_indices = {
        index
        for hit in hits
        for index in range(hit["runtimeStartIndex"], hit["runtimeEndExclusive"])
    }
    payload = {
        "trace": str(args.trace),
        "catalog": str(args.catalog),
        "runtimeByteCount": len(runtime_bytes),
        "hitCount": len(hits),
        "uniqueRecordCount": len({hit["recordId"] for hit in hits}),
        "matchedRuntimeByteCount": len(covered_indices),
        "unmatchedRuntimeByteCount": len(runtime_bytes) - len(covered_indices),
        "hits": hits,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Matched {len(hits)} catalog records from {len(runtime_bytes)} runtime bytes")


if __name__ == "__main__":
    main()
