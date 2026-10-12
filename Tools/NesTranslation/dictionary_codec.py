"""Expand byte-token dictionaries while preserving source-byte provenance."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .chr_records import ines_chr_layout


INES_HEADER_SIZE = 16
TRAINER_SIZE = 512


@dataclass(frozen=True)
class ExpandedToken:
    source_offset: int
    value: int
    kind: str
    dictionary_index: int | None
    expanded: tuple[int, ...]


def ines_prg(rom: bytes) -> bytes:
    if len(rom) < INES_HEADER_SIZE or rom[:4] != b"NES\x1a":
        raise ValueError("not an iNES ROM")
    trainer_size = TRAINER_SIZE if rom[6] & 0x04 else 0
    start = INES_HEADER_SIZE + trainer_size
    size = rom[4] * 16 * 1024
    if start + size > len(rom):
        raise ValueError("truncated PRG ROM section")
    return rom[start:start + size]


def read_dictionary(
    data: bytes,
    start: int,
    end_exclusive: int,
    terminator: int,
) -> tuple[bytes, ...]:
    if not 0 <= start < end_exclusive <= len(data):
        raise ValueError("dictionary range is outside its data section")
    if not 0 <= terminator <= 0xFF:
        raise ValueError("dictionary terminator must fit one byte")
    region = data[start:end_exclusive]
    entries: list[bytes] = []
    entry_start = 0
    for index, value in enumerate(region):
        if value == terminator:
            entries.append(region[entry_start:index])
            entry_start = index + 1
    if entry_start != len(region):
        raise ValueError("dictionary range does not end at a terminator")
    return tuple(entries)


def expand_tokens(
    source: bytes,
    dictionary: tuple[bytes, ...],
    token_base: int,
    *,
    source_offset: int = 0,
    modifier_values: frozenset[int] = frozenset(),
    control_minimum: int = 0xF0,
) -> tuple[ExpandedToken, ...]:
    if not 0 <= token_base <= 0xFF:
        raise ValueError("token base must fit one byte")
    token_end = token_base + len(dictionary)
    if token_end > 0x100:
        raise ValueError("dictionary token range exceeds one byte")
    result: list[ExpandedToken] = []
    for index, value in enumerate(source):
        dictionary_index = value - token_base
        if 0 <= dictionary_index < len(dictionary):
            kind = "dictionary"
            expanded = tuple(dictionary[dictionary_index])
            resolved_index: int | None = dictionary_index
        else:
            if value in modifier_values:
                kind = "modifier"
            elif value >= control_minimum:
                kind = "control"
            else:
                kind = "glyph"
            expanded = (value,)
            resolved_index = None
        result.append(ExpandedToken(
            source_offset=source_offset + index,
            value=value,
            kind=kind,
            dictionary_index=resolved_index,
            expanded=expanded,
        ))
    return tuple(result)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", required=True, type=Path)
    parser.add_argument("--chr-start", required=True, type=lambda v: int(v, 0))
    parser.add_argument("--chr-end", required=True, type=lambda v: int(v, 0))
    parser.add_argument("--dictionary-start", required=True, type=lambda v: int(v, 0))
    parser.add_argument("--dictionary-end", required=True, type=lambda v: int(v, 0))
    parser.add_argument("--dictionary-terminator", default="fa")
    parser.add_argument("--token-base", default="6d")
    parser.add_argument("--modifier", action="append", default=[])
    parser.add_argument("--control-minimum", default="f0")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    rom = args.rom.read_bytes()
    chr_layout = ines_chr_layout(rom)
    if not 0 <= args.chr_start < args.chr_end <= chr_layout.size:
        raise ValueError("CHR record range is outside CHR ROM")
    chr_data = rom[
        chr_layout.file_offset + args.chr_start:
        chr_layout.file_offset + args.chr_end
    ]
    dictionary = read_dictionary(
        ines_prg(rom),
        args.dictionary_start,
        args.dictionary_end,
        int(args.dictionary_terminator, 16),
    )
    expanded = expand_tokens(
        chr_data,
        dictionary,
        int(args.token_base, 16),
        source_offset=args.chr_start,
        modifier_values=frozenset(int(value, 16) for value in args.modifier),
        control_minimum=int(args.control_minimum, 16),
    )
    flattened = [value for token in expanded for value in token.expanded]
    payload = {
        "rom": str(args.rom),
        "chrRange": {
            "start": args.chr_start,
            "endExclusive": args.chr_end,
        },
        "dictionary": {
            "prgStart": args.dictionary_start,
            "prgEndExclusive": args.dictionary_end,
            "entryCount": len(dictionary),
            "tokenBase": int(args.token_base, 16),
        },
        "tokens": [asdict(token) for token in expanded],
        "flattenedHex": bytes(flattened).hex(" "),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Expanded {len(expanded)} source tokens to {len(flattened)} bytes "
        f"using {len(dictionary)} dictionary entries"
    )


if __name__ == "__main__":
    main()
