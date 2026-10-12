"""Export a lossless, offset-bearing catalog for a PRG text dictionary."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import unicodedata
from typing import Any

from .dictionary_codec import ines_prg
from .text_review import load_character_map, render_bytes


class VocabularyError(ValueError):
    """Raised when reviewed vocabulary is inconsistent with its catalog."""


def normalize_japanese(value: str) -> str:
    return unicodedata.normalize(
        "NFC", value.replace("゛", "\N{COMBINING KATAKANA-HIRAGANA VOICED SOUND MARK}")
        .replace("゜", "\N{COMBINING KATAKANA-HIRAGANA SEMI-VOICED SOUND MARK}")
    )


def _suggest_category(text: str) -> tuple[str, str]:
    if any(term in text for term in ("つるぎ", "おの", "こんぼう", "たけざお")):
        return "weapon", "weapon-name suffix or known weapon noun"
    if any(term in text for term in ("よろい", "ふく", "かたびら")):
        return "armor", "armor-name suffix or known armor noun"
    if text.endswith("たて"):
        return "shield", "shield-name suffix"
    if any(term in text for term in (
        "やくそう", "かぎ", "たいまつ", "せいすい", "つばさ", "うろこ",
        "ふえ", "ゆびわ", "しるし", "たてごと", "くびかざり", "いし",
        "つえ", "しずく", "おうじょのあい",
    )):
        return "item", "known inventory or key-item noun"
    if any(term in text for term in (
        "てにいれた", "みつけた", "もてません", "おかねが", "どれを", "なにを",
    )):
        return "system-template", "known system-message phrase"
    if "<" in text:
        return "unresolved", "contains unresolved glyph or control placeholders"
    return "phrase", "decoded dictionary phrase"


def build_dictionary_catalog(
    rom: bytes,
    *,
    start: int,
    end_exclusive: int,
    terminator: int,
    token_base: int,
    character_map: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    prg = ines_prg(rom)
    if not 0 <= start < end_exclusive <= len(prg):
        raise ValueError("dictionary range is outside PRG ROM")
    if not 0 <= token_base <= 0xFF or not 0 <= terminator <= 0xFF:
        raise ValueError("token base and terminator must fit one byte")
    entries = []
    entry_start = start
    for offset in range(start, end_exclusive):
        if prg[offset] != terminator:
            continue
        index = len(entries)
        token = token_base + index
        if token > 0xFF:
            raise ValueError("dictionary token range exceeds one byte")
        raw = prg[entry_start:offset]
        decoded = render_bytes(raw, character_map)
        normalized = normalize_japanese(decoded)
        category, category_reason = _suggest_category(normalized)
        entries.append({
            "id": f"dict-{token:02x}",
            "token": token,
            "index": index,
            "prgStart": entry_start,
            "prgEndExclusive": offset,
            "terminatorOffset": offset,
            "rawHex": raw.hex(" "),
            "decoded": decoded,
            "normalized": normalized,
            "unknownBytes": sorted({value for value in raw if value not in character_map}),
            "suggestedCategory": category,
            "categoryEvidence": category_reason,
            "confidence": "static-candidate",
        })
        entry_start = offset + 1
    if entry_start != end_exclusive:
        raise ValueError("dictionary range does not end at a terminator")
    return {
        "formatVersion": 1,
        "romSha256": hashlib.sha256(rom).hexdigest(),
        "source": {
            "section": "PRG",
            "start": start,
            "endExclusive": end_exclusive,
            "terminator": terminator,
            "tokenBase": token_base,
        },
        "summary": {
            "entryCount": len(entries),
            "resolvedEntryCount": sum(not item["unknownBytes"] for item in entries),
        },
        "entries": entries,
    }


def render_markdown(catalog: dict[str, Any]) -> str:
    lines = [
        "# Dragon Quest PRG dictionary review",
        "",
        f"- ROM SHA-256: `{catalog['romSha256']}`",
        f"- Entries: {catalog['summary']['entryCount']}",
        f"- Entries without unknown bytes: {catalog['summary']['resolvedEntryCount']}",
        "- Categories are review suggestions; every entry remains static-candidate.",
        "",
    ]
    for item in catalog["entries"]:
        unknown = item["unknownBytes"]
        lines.extend([
            f"## {item['id']} — `{item['suggestedCategory']}`",
            "",
            f"- Token: `${item['token']:02X}`",
            f"- PRG: `${item['prgStart']:04X}-${item['prgEndExclusive']:04X}`",
            "- Unknown: " + (
                ", ".join(f"`${value:02X}`" for value in unknown) if unknown else "None"
            ),
            "",
            "```text",
            item["normalized"],
            "```",
            "",
        ])
    return "\n".join(lines).rstrip() + "\n"


def validate_vocabulary(catalog: dict[str, Any], vocabulary: dict[str, Any]) -> None:
    by_id = {item["id"]: item for item in catalog.get("entries", [])}
    seen_ids: set[str] = set()
    seen_tokens: set[int] = set()
    for index, record in enumerate(vocabulary.get("records", [])):
        if not isinstance(record, dict):
            raise VocabularyError(f"vocabulary record {index} must be an object")
        record_id = record.get("id")
        token = record.get("token")
        if not isinstance(record_id, str) or record_id in seen_ids:
            raise VocabularyError(f"invalid or duplicate vocabulary id: {record_id}")
        if not isinstance(token, int) or token in seen_tokens:
            raise VocabularyError(f"invalid or duplicate vocabulary token: {token}")
        source = by_id.get(record_id)
        if source is None or source["token"] != token:
            raise VocabularyError(f"vocabulary source mismatch: {record_id}")
        for key in ("category", "sourceText", "translation", "display", "confidence"):
            if not isinstance(record.get(key), str) or not record[key]:
                raise VocabularyError(f"vocabulary {record_id}.{key} must be non-empty")
        if not source["unknownBytes"] and record["sourceText"] != source["normalized"]:
            raise VocabularyError(f"resolved source text mismatch: {record_id}")
        seen_ids.add(record_id)
        seen_tokens.add(token)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", required=True, type=Path)
    parser.add_argument("--character-map", required=True, type=Path)
    parser.add_argument("--dictionary-start", required=True, type=lambda value: int(value, 0))
    parser.add_argument("--dictionary-end", required=True, type=lambda value: int(value, 0))
    parser.add_argument("--dictionary-terminator", default="fa")
    parser.add_argument("--token-base", default="6d")
    parser.add_argument("--json-output", required=True, type=Path)
    parser.add_argument("--markdown-output", required=True, type=Path)
    parser.add_argument("--vocabulary", type=Path)
    args = parser.parse_args()
    catalog = build_dictionary_catalog(
        args.rom.read_bytes(),
        start=args.dictionary_start,
        end_exclusive=args.dictionary_end,
        terminator=int(args.dictionary_terminator, 16),
        token_base=int(args.token_base, 16),
        character_map=load_character_map(args.character_map),
    )
    if args.vocabulary is not None:
        validate_vocabulary(
            catalog, json.loads(args.vocabulary.read_text(encoding="utf-8"))
        )
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.markdown_output.write_text(render_markdown(catalog), encoding="utf-8")
    print(
        f"Exported {catalog['summary']['entryCount']} dictionary entries; "
        f"{catalog['summary']['resolvedEntryCount']} contain no unknown bytes"
    )


if __name__ == "__main__":
    main()
