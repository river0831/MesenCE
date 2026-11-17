"""Export every 8x8 NES CHR-ROM tile as labeled atlas images and JSON."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from .chr_records import ines_chr_layout
from .text_review import load_character_map


TILE_BYTES = 16
TILES_PER_TABLE = 256
TABLES_PER_BANK = 2
TILES_PER_BANK = TILES_PER_TABLE * TABLES_PER_BANK


def decode_tile(pattern: bytes) -> tuple[tuple[int, ...], ...]:
    """Decode one NES 2bpp planar tile into an 8x8 matrix of values 0..3."""
    if len(pattern) != TILE_BYTES:
        raise ValueError("one CHR tile must contain exactly 16 bytes")
    rows = []
    for y in range(8):
        low, high = pattern[y], pattern[y + 8]
        rows.append(tuple(
            ((low >> (7 - x)) & 1) | (((high >> (7 - x)) & 1) << 1)
            for x in range(8)
        ))
    return tuple(rows)


def _font(size: int) -> ImageFont.ImageFont:
    candidates = (
        "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    )
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            pass
    return ImageFont.load_default()


def render_bank_atlas(
    chr_data: bytes,
    bank: int,
    labels: dict[int, str],
    output: Path,
    *,
    game_name: str = "NES ROM",
    scale: int = 4,
) -> None:
    columns, rows = 16, 32
    tile_size = 8 * scale
    label_height = 16
    header_height = 34
    cell_width = max(tile_size + 8, 48)
    cell_height = tile_size + label_height + 8
    image = Image.new(
        "RGB", (columns * cell_width, header_height + rows * cell_height),
        (20, 22, 26),
    )
    draw = ImageDraw.Draw(image)
    small = _font(10)
    title = _font(16)
    draw.text(
        (8, 7),
        f"{game_name} — CHR bank {bank} — tables {bank * 2}/{bank * 2 + 1}",
        fill=(240, 240, 240), font=title,
    )
    palette = ((0, 0, 0), (92, 92, 92), (180, 180, 180), (255, 255, 255))
    bank_start = bank * TILES_PER_BANK * TILE_BYTES
    for local_index in range(TILES_PER_BANK):
        absolute_index = bank * TILES_PER_BANK + local_index
        pattern_start = bank_start + local_index * TILE_BYTES
        pixels = decode_tile(chr_data[pattern_start:pattern_start + TILE_BYTES])
        column, row = local_index % columns, local_index // columns
        x = column * cell_width
        y = header_height + row * cell_height
        for pixel_y, values in enumerate(pixels):
            for pixel_x, value in enumerate(values):
                draw.rectangle(
                    (
                        x + 4 + pixel_x * scale,
                        y + 4 + pixel_y * scale,
                        x + 4 + (pixel_x + 1) * scale - 1,
                        y + 4 + (pixel_y + 1) * scale - 1,
                    ),
                    fill=palette[value],
                )
        table = local_index // TILES_PER_TABLE
        tile = local_index % TILES_PER_TABLE
        label = f"T{table} {tile:02X}"
        known = labels.get(tile) if table == 0 else None
        if known:
            label += f" {known}"
        draw.text(
            (x + 3, y + tile_size + 5), label,
            fill=(255, 211, 64) if known else (160, 170, 180), font=small,
        )
        draw.rectangle(
            (x, y, x + cell_width - 1, y + cell_height - 1),
            outline=(55, 59, 67),
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)


def export_chr_atlas(
    rom_path: Path, output_dir: Path, character_map_path: Path | None = None
) -> dict[str, Any]:
    rom = rom_path.read_bytes()
    layout = ines_chr_layout(rom)
    chr_data = rom[layout.file_offset:layout.file_offset + layout.size]
    labels = {}
    if character_map_path is not None:
        labels = {
            value: str(entry["display"])
            for value, entry in load_character_map(character_map_path).items()
            if entry.get("type") in ("glyph", "modifier")
        }
    if len(chr_data) % (TILES_PER_BANK * TILE_BYTES):
        raise ValueError("CHR size is not an integral number of 8 KiB banks")
    bank_count = len(chr_data) // (TILES_PER_BANK * TILE_BYTES)
    output_dir.mkdir(parents=True, exist_ok=True)
    tiles = []
    for bank in range(bank_count):
        render_bank_atlas(
            chr_data, bank, labels, output_dir / f"chr-bank-{bank}.png",
            game_name=rom_path.stem,
        )
        for local_index in range(TILES_PER_BANK):
            start = (bank * TILES_PER_BANK + local_index) * TILE_BYTES
            pattern = chr_data[start:start + TILE_BYTES]
            table = local_index // TILES_PER_TABLE
            tile = local_index % TILES_PER_TABLE
            tiles.append({
                "bank": bank,
                "patternTable": table,
                "tileIndex": tile,
                "globalTileIndex": bank * TILES_PER_BANK + local_index,
                "chrOffset": start,
                "patternHex": pattern.hex(),
                "patternSha256": hashlib.sha256(pattern).hexdigest(),
                "knownCharacter": labels.get(tile) if table == 0 else None,
                "blank": not any(pattern),
            })
    manifest = {
        "formatVersion": 1,
        "rom": str(rom_path),
        "romSha256": hashlib.sha256(rom).hexdigest(),
        "chrFileOffset": layout.file_offset,
        "chrSize": layout.size,
        "bankCount": bank_count,
        "tileCount": len(tiles),
        "uniquePatternCount": len({item["patternHex"] for item in tiles}),
        "tiles": tiles,
    }
    (output_dir / "chr-tiles.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--character-map", type=Path)
    args = parser.parse_args()
    manifest = export_chr_atlas(
        args.rom, args.output_dir, args.character_map
    )
    print(
        f"Exported {manifest['tileCount']} tiles "
        f"({manifest['uniquePatternCount']} unique patterns) "
        f"from {manifest['bankCount']} CHR banks to {args.output_dir}"
    )


if __name__ == "__main__":
    main()
