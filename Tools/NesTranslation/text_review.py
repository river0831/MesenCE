"""Render expanded byte streams with an evidence-bearing character map."""

from __future__ import annotations

import argparse
import json
import unicodedata
from pathlib import Path
from typing import Any


def load_character_map(path: Path) -> dict[int, dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    entries = raw.get("entries")
    if not isinstance(entries, dict):
        raise ValueError("character map entries must be an object")
    result: dict[int, dict[str, Any]] = {}
    for key, value in entries.items():
        byte = int(key, 16)
        if not 0 <= byte <= 0xFF or not isinstance(value, dict):
            raise ValueError(f"invalid character map entry: {key}")
        for required in ("display", "type", "confidence", "evidence"):
            if not isinstance(value.get(required), str):
                raise ValueError(f"character map {key}.{required} must be a string")
        result[byte] = value
    return result


def render_bytes(values: list[int], character_map: dict[int, dict[str, Any]]) -> str:
    output: list[str] = []
    for value in values:
        entry = character_map.get(value)
        if entry is None:
            output.append(f"<{value:02X}>")
            continue
        if entry["type"] == "modifier" and output:
            combining = entry.get("combiningDisplay")
            if isinstance(combining, str):
                output[-1] = unicodedata.normalize("NFC", output[-1] + combining)
                continue
        output.append(entry["display"])
    return "".join(output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expanded", required=True, type=Path)
    parser.add_argument("--character-map", required=True, type=Path)
    parser.add_argument("--confidence", default="semantic-probable")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    expanded = json.loads(args.expanded.read_text(encoding="utf-8"))
    flattened_hex = expanded.get("flattenedHex")
    if not isinstance(flattened_hex, str):
        raise ValueError("expanded input lacks flattenedHex")
    values = list(bytes.fromhex(flattened_hex))
    character_map = load_character_map(args.character_map)
    rendered = render_bytes(values, character_map)

    unknown = sorted({value for value in values if value not in character_map})
    lines = [
        "# Dragon Quest CHR dialogue review",
        "",
        f"- CHR range: `${expanded['chrRange']['start']:04X}-${expanded['chrRange']['endExclusive']:04X}`",
        f"- Source tokens: {len(expanded['tokens'])}",
        f"- Expanded bytes: {len(values)}",
        f"- Confidence: {args.confidence}",
        "",
        "## Decoded text",
        "",
        "```text",
        rendered,
        "```",
        "",
        "## Unknown bytes",
        "",
        ", ".join(f"`${value:02X}`" for value in unknown) if unknown else "None.",
        "",
        "## Expanded bytes",
        "",
        f"`{flattened_hex}`",
        "",
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines), encoding="utf-8")
    print(f"Rendered review to {args.output}; unknown byte count={len(unknown)}")


if __name__ == "__main__":
    main()
