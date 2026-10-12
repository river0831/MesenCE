"""Losslessly split candidate records from the CHR section of an iNES ROM."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path


INES_HEADER_SIZE = 16
TRAINER_SIZE = 512


@dataclass(frozen=True)
class ChrLayout:
    file_offset: int
    size: int


@dataclass(frozen=True)
class ChrRecord:
    chr_start: int
    chr_end_exclusive: int
    file_start: int
    file_end_exclusive: int
    terminator: int
    raw_hex: str


def ines_chr_layout(rom: bytes) -> ChrLayout:
    if len(rom) < INES_HEADER_SIZE or rom[:4] != b"NES\x1a":
        raise ValueError("not an iNES ROM")
    prg_size = rom[4] * 16 * 1024
    chr_size = rom[5] * 8 * 1024
    trainer_size = TRAINER_SIZE if rom[6] & 0x04 else 0
    file_offset = INES_HEADER_SIZE + trainer_size + prg_size
    if chr_size == 0:
        raise ValueError("ROM has no CHR ROM section")
    if file_offset + chr_size > len(rom):
        raise ValueError("truncated CHR ROM section")
    return ChrLayout(file_offset=file_offset, size=chr_size)


def split_chr_records(
    rom: bytes,
    terminator: int,
    *,
    minimum_length: int = 1,
    maximum_length: int = 256,
) -> tuple[ChrRecord, ...]:
    if not 0 <= terminator <= 0xFF:
        raise ValueError("terminator must fit one byte")
    if minimum_length <= 0 or maximum_length < minimum_length:
        raise ValueError("invalid record length bounds")
    layout = ines_chr_layout(rom)
    chr_data = rom[layout.file_offset:layout.file_offset + layout.size]
    records: list[ChrRecord] = []
    start = 0
    for index, value in enumerate(chr_data):
        if value != terminator:
            continue
        end = index + 1
        length = end - start
        if minimum_length <= length <= maximum_length:
            raw = chr_data[start:end]
            records.append(ChrRecord(
                chr_start=start,
                chr_end_exclusive=end,
                file_start=layout.file_offset + start,
                file_end_exclusive=layout.file_offset + end,
                terminator=terminator,
                raw_hex=raw.hex(" "),
            ))
        start = end
    return tuple(records)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", required=True, type=Path)
    parser.add_argument("--terminator", default="fc")
    parser.add_argument("--minimum-length", type=int, default=2)
    parser.add_argument("--maximum-length", type=int, default=256)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    terminator = int(args.terminator, 16)
    records = split_chr_records(
        args.rom.read_bytes(),
        terminator,
        minimum_length=args.minimum_length,
        maximum_length=args.maximum_length,
    )
    payload = {
        "rom": str(args.rom),
        "terminator": terminator,
        "records": [asdict(record) for record in records],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Exported {len(records)} CHR record candidates to {args.output}")


if __name__ == "__main__":
    main()
