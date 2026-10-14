"""Build a reviewable CHR text-candidate catalog without discarding bytes."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .chr_records import ines_chr_layout, split_chr_records
from .dictionary_codec import expand_tokens, ines_prg, read_dictionary
from .text_review import load_character_map, render_bytes


MESSAGE_SEPARATOR_SUFFIX = frozenset((0xFE, 0x57, 0xFB))


def extract_message_units(
    raw: bytes,
    *,
    chr_start: int,
    file_start: int,
    dictionary: tuple[bytes, ...],
    token_base: int,
    character_map: dict[int, dict[str, Any]],
    modifier_values: frozenset[int],
    control_minimum: int,
) -> list[dict[str, Any]]:
    """Split one lossless FC container at raw FF message-entry boundaries.

    FC remains the only confirmed container terminator. FF is retained as a
    statically inferred inner boundary; adjacent layout bytes are recorded as
    the separator rather than assigned to either message's visible content.
    """
    payload_end = len(raw) - 1 if raw and raw[-1] == 0xFC else len(raw)
    units: list[dict[str, Any]] = []
    unit_start = 0
    boundaries = [index for index, value in enumerate(raw[:payload_end]) if value == 0xFF]
    for ordinal, boundary in enumerate(boundaries + [payload_end]):
        separator_end = boundary + 1 if boundary < payload_end else boundary
        content_end = boundary
        if boundary < payload_end:
            while content_end > unit_start and raw[content_end - 1] in MESSAGE_SEPARATOR_SUFFIX:
                content_end -= 1
        content = raw[unit_start:content_end]
        separator = raw[content_end:separator_end]
        if content:
            tokens = expand_tokens(
                content,
                dictionary,
                token_base,
                source_offset=chr_start + unit_start,
                modifier_values=modifier_values,
                control_minimum=control_minimum,
            )
            expanded = [value for token in tokens for value in token.expanded]
            units.append({
                "id": f"chr-fc-{chr_start:04x}-u{len(units) + 1}",
                "ordinal": len(units) + 1,
                "source": {
                    "containerId": f"chr-fc-{chr_start:04x}",
                    "chrStart": chr_start + unit_start,
                    "chrEndExclusive": chr_start + content_end,
                    "fileStart": file_start + unit_start,
                    "fileEndExclusive": file_start + content_end,
                },
                "rawHex": content.hex(" "),
                "expandedHex": bytes(expanded).hex(" "),
                "decoded": render_bytes(expanded, character_map),
                "separatorHex": separator.hex(" "),
                "boundaryConfidence": (
                    "static-ff-boundary" if separator else "container-terminator"
                ),
                "tokens": [asdict(token) for token in tokens],
            })
        unit_start = separator_end
    return units


def analyze_record(
    raw: bytes,
    *,
    chr_start: int,
    file_start: int,
    dictionary: tuple[bytes, ...],
    token_base: int,
    character_map: dict[int, dict[str, Any]],
    modifier_values: frozenset[int],
    control_minimum: int,
) -> dict[str, Any]:
    expanded_tokens = expand_tokens(
        raw,
        dictionary,
        token_base,
        source_offset=chr_start,
        modifier_values=modifier_values,
        control_minimum=control_minimum,
    )
    expanded = [value for token in expanded_tokens for value in token.expanded]
    known = [value in character_map for value in expanded]
    raw_resolvable = [
        value in character_map or token_base <= value < token_base + len(dictionary)
        for value in raw
    ]
    glyph_count = sum(
        character_map[value]["type"] == "glyph"
        for value in expanded
        if value in character_map
    )
    unknown = sorted({value for value in expanded if value not in character_map})
    known_ratio = sum(known) / len(known) if known else 0.0
    raw_resolvable_ratio = (
        sum(raw_resolvable) / len(raw_resolvable) if raw_resolvable else 0.0
    )
    glyph_ratio = glyph_count / len(expanded) if expanded else 0.0
    has_dialogue_prefix = 0x55 in expanded and 0x62 in expanded
    has_layout_control = any(value in expanded for value in (0xF2, 0xFE))
    meaningful_length = glyph_count >= 6

    # This is intentionally a ranking heuristic, not a text/non-text verdict.
    # Bitmap data can coincidentally use the same byte values as dictionary tokens.
    score = (
        0.50 * known_ratio
        + 0.25 * raw_resolvable_ratio
        + 0.15 * min(glyph_ratio / 0.65, 1.0)
        + (0.05 if has_dialogue_prefix else 0.0)
        + (0.03 if has_layout_control else 0.0)
        + (0.02 if meaningful_length else 0.0)
    )
    score = min(score, 1.0)
    if score >= 0.88 and meaningful_length:
        likelihood = "high"
    elif score >= 0.75 and meaningful_length:
        likelihood = "medium"
    else:
        likelihood = "low"

    message_units = extract_message_units(
        raw,
        chr_start=chr_start,
        file_start=file_start,
        dictionary=dictionary,
        token_base=token_base,
        character_map=character_map,
        modifier_values=modifier_values,
        control_minimum=control_minimum,
    )
    return {
        "id": f"chr-fc-{chr_start:04x}",
        "source": {
            "section": "CHR",
            "chrStart": chr_start,
            "chrEndExclusive": chr_start + len(raw),
            "fileStart": file_start,
            "fileEndExclusive": file_start + len(raw),
        },
        "terminator": raw[-1] if raw else None,
        "rawHex": raw.hex(" "),
        "expandedHex": bytes(expanded).hex(" "),
        "decoded": render_bytes(expanded, character_map),
        "unknownBytes": unknown,
        "metrics": {
            "sourceByteCount": len(raw),
            "expandedByteCount": len(expanded),
            "glyphCount": glyph_count,
            "knownRatio": round(known_ratio, 4),
            "rawResolvableRatio": round(raw_resolvable_ratio, 4),
            "score": round(score, 4),
        },
        "evidence": {
            "hasDialoguePrefix": has_dialogue_prefix,
            "hasLayoutControl": has_layout_control,
            "likelihood": likelihood,
            "confidence": "static-candidate",
        },
        "translation": None,
        "runtime": {
            "status": "unverified",
            "observedReadAddress": None,
            "notes": None,
        },
        "tokens": [asdict(token) for token in expanded_tokens],
        "messageUnitCount": len(message_units),
        "messageUnits": message_units,
        "segmentation": {
            "containerTerminator": 0xFC,
            "messageBoundary": 0xFF,
            "messageBoundaryConfidence": "static-inferred",
            "notes": "FF boundaries are extracted generically; runtime entry-point tracing remains the confirmation step",
        },
    }


def build_catalog(
    rom: bytes,
    *,
    dictionary_start: int,
    dictionary_end: int,
    dictionary_terminator: int,
    token_base: int,
    record_terminator: int,
    character_map: dict[int, dict[str, Any]],
    minimum_length: int = 2,
    maximum_length: int = 256,
    modifier_values: frozenset[int] = frozenset(),
    control_minimum: int = 0xF0,
) -> dict[str, Any]:
    layout = ines_chr_layout(rom)
    dictionary = read_dictionary(
        ines_prg(rom), dictionary_start, dictionary_end, dictionary_terminator
    )
    records = split_chr_records(
        rom,
        record_terminator,
        minimum_length=minimum_length,
        maximum_length=maximum_length,
    )
    analyzed = [
        analyze_record(
            bytes.fromhex(record.raw_hex),
            chr_start=record.chr_start,
            file_start=record.file_start,
            dictionary=dictionary,
            token_base=token_base,
            character_map=character_map,
            modifier_values=modifier_values,
            control_minimum=control_minimum,
        )
        for record in records
    ]
    counts = {
        likelihood: sum(
            record["evidence"]["likelihood"] == likelihood for record in analyzed
        )
        for likelihood in ("high", "medium", "low")
    }
    message_unit_count = sum(record["messageUnitCount"] for record in analyzed)
    multi_unit_count = sum(record["messageUnitCount"] > 1 for record in analyzed)
    return {
        "formatVersion": 1,
        "romSha256": hashlib.sha256(rom).hexdigest(),
        "source": {
            "section": "CHR",
            "fileOffset": layout.file_offset,
            "size": layout.size,
            "recordTerminator": record_terminator,
        },
        "dictionary": {
            "section": "PRG",
            "start": dictionary_start,
            "endExclusive": dictionary_end,
            "terminator": dictionary_terminator,
            "tokenBase": token_base,
            "entryCount": len(dictionary),
        },
        "summary": {
            "recordCount": len(analyzed),
            "messageUnitCount": message_unit_count,
            "multiUnitContainerCount": multi_unit_count,
            **counts,
        },
        "records": analyzed,
    }


def render_catalog_review(catalog: dict[str, Any], include: set[str]) -> str:
    summary = catalog["summary"]
    lines = [
        "# Dragon Quest CHR dialogue candidate review",
        "",
        f"- ROM SHA-256: `{catalog['romSha256']}`",
        f"- Lossless `$FC` records analyzed: {summary['recordCount']}",
        f"- High likelihood: {summary['high']}",
        f"- Medium likelihood: {summary['medium']}",
        f"- Low likelihood: {summary['low']}",
        "- Classification: static heuristic only; no candidate is runtime-confirmed by this report",
        "",
    ]
    for record in catalog["records"]:
        likelihood = record["evidence"]["likelihood"]
        if likelihood not in include:
            continue
        source = record["source"]
        metrics = record["metrics"]
        unknown = record["unknownBytes"]
        lines.extend([
            f"## {record['id']} — {likelihood}",
            "",
            f"- CHR: `${source['chrStart']:04X}-${source['chrEndExclusive']:04X}`",
            f"- File: `${source['fileStart']:04X}-${source['fileEndExclusive']:04X}`",
            f"- Score: {metrics['score']:.4f}; known: {metrics['knownRatio']:.4f}",
            "- Unknown: " + (", ".join(f"`${value:02X}`" for value in unknown) if unknown else "None"),
            "",
            "```text",
            record["decoded"],
            "```",
            "",
        ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", required=True, type=Path)
    parser.add_argument("--character-map", required=True, type=Path)
    parser.add_argument("--dictionary-start", required=True, type=lambda v: int(v, 0))
    parser.add_argument("--dictionary-end", required=True, type=lambda v: int(v, 0))
    parser.add_argument("--dictionary-terminator", default="fa")
    parser.add_argument("--token-base", default="6d")
    parser.add_argument("--record-terminator", default="fc")
    parser.add_argument("--modifier", action="append", default=[])
    parser.add_argument("--control-minimum", default="f0")
    parser.add_argument("--minimum-length", type=int, default=2)
    parser.add_argument("--maximum-length", type=int, default=256)
    parser.add_argument("--catalog-output", required=True, type=Path)
    parser.add_argument("--review-output", required=True, type=Path)
    parser.add_argument(
        "--review-likelihood",
        action="append",
        choices=("high", "medium", "low"),
        default=[],
    )
    args = parser.parse_args()

    catalog = build_catalog(
        args.rom.read_bytes(),
        dictionary_start=args.dictionary_start,
        dictionary_end=args.dictionary_end,
        dictionary_terminator=int(args.dictionary_terminator, 16),
        token_base=int(args.token_base, 16),
        record_terminator=int(args.record_terminator, 16),
        character_map=load_character_map(args.character_map),
        minimum_length=args.minimum_length,
        maximum_length=args.maximum_length,
        modifier_values=frozenset(int(value, 16) for value in args.modifier),
        control_minimum=int(args.control_minimum, 16),
    )
    args.catalog_output.parent.mkdir(parents=True, exist_ok=True)
    args.catalog_output.write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    include = set(args.review_likelihood or ("high",))
    args.review_output.parent.mkdir(parents=True, exist_ok=True)
    args.review_output.write_text(
        render_catalog_review(catalog, include) + "\n", encoding="utf-8"
    )
    summary = catalog["summary"]
    print(
        f"Analyzed {summary['recordCount']} records: {summary['high']} high, "
        f"{summary['medium']} medium, {summary['low']} low"
    )


if __name__ == "__main__":
    main()
