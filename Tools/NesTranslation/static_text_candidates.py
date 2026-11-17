"""Extract lossless, confidence-ranked text-like byte runs from NES PRG ROM."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .dictionary_codec import ines_prg


def load_profile(path: Path) -> dict[str, Any]:
    profile = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(profile.get("ranges"), list):
        raise ValueError("font profile requires ranges")
    return profile


def profile_map(profile: dict[str, Any]) -> dict[int, str]:
    result: dict[int, str] = {}
    for item in profile["ranges"]:
        start, text = item.get("start"), item.get("text")
        if not isinstance(start, int) or not isinstance(text, str):
            raise ValueError("font ranges require integer start and text")
        for offset, character in enumerate(text):
            value = start + offset
            if not 0 <= value <= 0xFF or value in result:
                raise ValueError("font ranges overlap or exceed one byte")
            result[value] = character
    for key, value in profile.get("symbols", {}).items():
        result[int(key, 16)] = str(value)
    return result


def _score(text: str, raw: bytes, minimum_length: int) -> tuple[str, list[str]]:
    visible = [character for character in text if not character.isspace()]
    japanese = sum(ord(character) >= 0x3000 for character in visible)
    letters = sum(character.isalpha() or character.isdigit() for character in visible)
    repeated = max((raw.count(bytes((value,))) for value in set(raw)), default=0)
    reasons = []
    if len(visible) >= max(minimum_length, 5):
        reasons.append("sufficient-length")
    if japanese >= 4:
        reasons.append("japanese-sequence")
    if letters >= 5:
        reasons.append("alphanumeric-sequence")
    if repeated > max(6, len(raw) * 3 // 4):
        reasons.append("heavy-repetition")
    if (japanese >= 4 or letters >= 6) and "heavy-repetition" not in reasons:
        return "high", reasons
    if len(visible) >= minimum_length and "heavy-repetition" not in reasons:
        return "medium", reasons
    return "low", reasons


def extract_candidates(
    rom: bytes, profile: dict[str, Any]
) -> dict[str, Any]:
    prg = ines_prg(rom)
    mapping = profile_map(profile)
    minimum_length = int(profile.get("minimumLength", 2))
    joiners = {
        int(key, 16): str(value)
        for key, value in profile.get("joiners", {}).items()
    }
    accepted = set(mapping) | set(joiners)
    records = []
    start: int | None = None
    values: list[int] = []

    def finish(end: int) -> None:
        nonlocal start, values
        if start is None:
            return
        glyph_count = sum(value in mapping for value in values)
        if glyph_count >= minimum_length:
            text = "".join(mapping.get(value, joiners.get(value, "")) for value in values)
            confidence, reasons = _score(text, bytes(values), minimum_length)
            records.append({
                "id": f"prg-{start:06x}",
                "prgStart": start,
                "prgEndExclusive": end,
                "rawHex": bytes(values).hex(" "),
                "sourceText": text,
                "glyphCount": glyph_count,
                "confidence": confidence,
                "confidenceReasons": reasons,
                "translation": None,
                "translationStatus": "pending",
            })
        start, values = None, []

    for offset, value in enumerate(prg):
        if value in accepted:
            if start is None:
                start = offset
            values.append(value)
        else:
            finish(offset)
    finish(len(prg))
    counts = {
        level: sum(record["confidence"] == level for record in records)
        for level in ("high", "medium", "low")
    }
    return {
        "formatVersion": 1,
        "game": profile.get("game"),
        "romSha256": hashlib.sha256(rom).hexdigest(),
        "extractionMethod": "contiguous-profile-byte-runs",
        "limitations": [
            "Static candidates can include code, maps, graphics, and lookup tables.",
            "Compression and dictionary tokens are not expanded until game-specific decoders are known.",
        ],
        "summary": {"recordCount": len(records), **counts},
        "records": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", required=True, type=Path)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = extract_candidates(args.rom.read_bytes(), load_profile(args.profile))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
