#!/usr/bin/env python3
"""Capture live Nametable tiles and compare their PPU patterns with CHR-ROM."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import subprocess
import sys
import unicodedata
import zlib
from pathlib import Path


def ines_chr(rom: bytes) -> bytes:
    trainer = 512 if rom[6] & 0x04 else 0
    start = 16 + trainer + rom[4] * 0x4000
    return rom[start : start + rom[5] * 0x2000]


def decode(pattern: bytes) -> list[list[int]]:
    pixels = []
    for y in range(8):
        pixels.append([
            ((pattern[y] >> (7 - x)) & 1) | (((pattern[y + 8] >> (7 - x)) & 1) << 1)
            for x in range(8)
        ])
    return pixels


def canvas(width: int, height: int, color: tuple[int, int, int]) -> dict:
    return {"width": width, "height": height, "pixels": bytearray(color * (width * height))}


def put_pixel(image: dict, x: int, y: int, color: tuple[int, int, int]) -> None:
    if x < 0 or y < 0 or x >= image["width"] or y >= image["height"]:
        return
    offset = (y * image["width"] + x) * 3
    image["pixels"][offset : offset + 3] = bytes(color)


def save_png(image: dict, path: Path) -> None:
    width, height = image["width"], image["height"]
    pixels = image["pixels"]
    raw = b"".join(b"\x00" + bytes(pixels[y * width * 3 : (y + 1) * width * 3]) for y in range(height))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def paint_tile(image: dict, pattern: bytes, x0: int, y0: int, scale: int = 4) -> None:
    colors = ((0, 0, 0), (255, 255, 255), (150, 150, 150), (80, 80, 80))
    for y, row in enumerate(decode(pattern)):
        for x, value in enumerate(row):
            for yy in range(scale):
                for xx in range(scale):
                    put_pixel(image, x0 + x * scale + xx, y0 + y * scale + yy, colors[value])


def chr_index(chr_data: bytes) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = {}
    for offset in range(0, len(chr_data), 16):
        signature = chr_data[offset : offset + 16].hex()
        result.setdefault(signature, []).append({
            "chrBank": offset // 0x2000,
            "patternTable": (offset % 0x2000) // 0x1000,
            "tileId": (offset % 0x1000) // 16,
            "chrOffset": offset,
        })
    return result


def render_nametables(tiles: bytes, patterns: dict[str, str], output: Path) -> None:
    # CIRAM has two physical 32x30 pages. Show them side by side.
    scale = 3
    image = canvas(64 * 8 * scale, 30 * 8 * scale, (0, 0, 0))
    for page in range(2):
        for cell in range(0x3C0):
            tile = tiles[page * 0x400 + cell]
            pattern_hex = patterns.get(f"{tile:02X}")
            if not pattern_hex:
                continue
            x = (page * 32 + cell % 32) * 8 * scale
            y = (cell // 32) * 8 * scale
            paint_tile(image, bytes.fromhex(pattern_hex), x, y, scale)
    save_png(image, output)


def render_dakuten(sample: dict, output: Path) -> None:
    scale = 16
    image = canvas(592, 176, (24, 24, 24))
    voiced = bytes.fromhex(sample["voicedPatternHex"])
    chr_base = bytes.fromhex(sample["unvoicedPatternHex"])
    positions = (24, 232, 440)
    paint_tile(image, voiced, positions[0], 24, scale)
    paint_tile(image, chr_base, positions[1], 24, scale)

    voiced_pixels = decode(voiced)
    base_pixels = decode(chr_base)
    diff = bytes(16)
    # Paint a binary difference matrix: magenta means the 2-bit pixel differs.
    for y in range(8):
        for x in range(8):
            color = (255, 40, 190) if voiced_pixels[y][x] != base_pixels[y][x] else (10, 10, 10)
            for yy in range(scale):
                for xx in range(scale):
                    put_pixel(image, positions[2] + x * scale + xx, 24 + y * scale + yy, color)

    # One grid cell equals exactly one original NES pixel.
    for x0 in positions:
        for index in range(9):
            gx = x0 + index * scale
            gy = 24 + index * scale
            for y in range(24, 24 + 8 * scale + 1):
                put_pixel(image, gx, y, (0, 210, 255))
            for x in range(x0, x0 + 8 * scale + 1):
                put_pixel(image, x, gy, (0, 210, 255))
    save_png(image, output)


def render_candidate_sheet(candidates: list[dict], output: Path) -> None:
    """Render up to 12 candidate/base pairs; JSON carries their identities."""
    scale = 6
    cell = 8 * scale
    gap = 16
    rows = candidates[:12]
    image = canvas(cell * 2 + gap * 3, max(1, len(rows)) * (cell + gap) + gap, (24, 24, 24))
    for row, sample in enumerate(rows):
        y0 = gap + row * (cell + gap)
        for column, key in enumerate(("patternHex", "nearestBasePatternHex")):
            x0 = gap + column * (cell + gap)
            paint_tile(image, bytes.fromhex(sample[key]), x0, y0, scale)
            for index in range(9):
                for y in range(y0, y0 + cell + 1):
                    put_pixel(image, x0 + index * scale, y, (0, 210, 255))
                for x in range(x0, x0 + cell + 1):
                    put_pixel(image, x, y0 + index * scale, (0, 210, 255))
    save_png(image, output)


def render_confirmed_sheet(samples: list[dict], output: Path) -> None:
    """Render each runtime 3x3 neighborhood plus its source base glyph."""
    scale = 6
    tile_size = 8 * scale
    gap = 16
    rows = [sample for sample in samples if sample.get("basePatternHex")][:8]
    width = tile_size * 4 + gap * 3
    height = max(1, len(rows)) * (tile_size * 3 + gap) + gap
    image = canvas(width, height, (24, 24, 24))
    for sample_index, sample in enumerate(rows):
        y_base = gap + sample_index * (tile_size * 3 + gap)
        by_position = {(cell["dx"], cell["dy"]): cell for cell in sample.get("neighborhood", [])}
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                cell = by_position.get((dx, dy))
                if not cell:
                    continue
                x0 = (dx + 1) * tile_size
                y0 = y_base + (dy + 1) * tile_size
                paint_tile(image, bytes.fromhex(cell["patternHex"]), x0, y0, scale)
                border = (255, 50, 190) if dx == 0 and dy == 0 else (0, 210, 255)
                for x in range(x0, x0 + tile_size + 1):
                    put_pixel(image, x, y0, border)
                    put_pixel(image, x, y0 + tile_size, border)
                for y in range(y0, y0 + tile_size + 1):
                    put_pixel(image, x0, y, border)
                    put_pixel(image, x0 + tile_size, y, border)
        base_x = tile_size * 3 + gap * 2
        base_y = y_base + tile_size
        paint_tile(image, bytes.fromhex(sample["basePatternHex"]), base_x, base_y, scale)
        for index in range(9):
            for y in range(base_y, base_y + tile_size + 1):
                put_pixel(image, base_x + index * scale, y, (255, 190, 0))
            for x in range(base_x, base_x + tile_size + 1):
                put_pixel(image, x, base_y + index * scale, (255, 190, 0))
    save_png(image, output)


VOICABLE_BASES = {
    0x0F: "か", 0x10: "き", 0x11: "く", 0x12: "け", 0x13: "こ",
    0x14: "さ", 0x15: "し", 0x16: "す", 0x17: "せ", 0x18: "そ",
    0x19: "た", 0x1A: "ち", 0x1B: "つ", 0x1C: "て", 0x1D: "と",
    0x23: "は", 0x24: "ひ", 0x25: "ふ", 0x26: "へ", 0x27: "ほ",
}


def confirmed_voice_sample(event: dict, chr_patterns: dict[str, list[dict]]) -> dict:
    base_character = VOICABLE_BASES.get(event["sourceBase"])
    logical_character = None
    if base_character and event["modifier"] == 0xF8:
        logical_character = unicodedata.normalize("NFC", base_character + "\u3099")
    within = event["ciramAddress"] % 0x400
    pattern_hex = event["patternHex"]
    base_hex = event.get("basePatternHex", "")
    return {
        "status": "source-write-confirmed",
        "identityConfirmed": logical_character is not None,
        "frame": event["frame"],
        "sourceEncoding": [event["sourceBase"], event["modifier"]],
        "baseCharacter": base_character,
        "logicalCharacter": logical_character,
        "ppuAddress": event["ppuAddress"],
        "ciramAddress": event["ciramAddress"],
        "page": event["ciramAddress"] // 0x400,
        "row": within // 32,
        "column": within % 32,
        "tileId": event["tileId"],
        "patternBase": event["patternBase"],
        "patternHex": pattern_hex,
        "basePatternHex": base_hex,
        "differentPixels": pixel_difference(bytes.fromhex(pattern_hex), bytes.fromhex(base_hex)) if base_hex else None,
        "perfectChrMatches": chr_patterns.get(pattern_hex, []),
        "basePerfectChrMatches": chr_patterns.get(base_hex, []),
        "neighborhood": event.get("neighborhood", []),
    }


def save_confirmed_samples(samples: list[dict], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "session-confirmed-voicing-samples.json").write_text(
        json.dumps({"sampleCount": len(samples), "samples": samples}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    render_confirmed_sheet(samples, output / "session-confirmed-voicing-samples.png")


def pixel_difference(left: bytes, right: bytes) -> int:
    """Count different 2-bit pixels; this is a ranking hint, not identity."""
    return sum(
        a != b
        for left_row, right_row in zip(decode(left), decode(right))
        for a, b in zip(left_row, right_row)
    )


def visible_occurrences(tiles: bytes, tile_id: int) -> list[dict]:
    result = []
    for address, value in enumerate(tiles):
        within = address % 0x400
        if within >= 0x3C0 or value != tile_id:
            continue
        result.append({
            "ciramAddress": address,
            "page": address // 0x400,
            "row": within // 32,
            "column": within % 32,
        })
    return result


def shape_candidates(tiles: bytes, patterns: dict[str, str]) -> list[dict]:
    """Rank visible non-base tiles against voicable kana base glyphs.

    These results deliberately carry no Japanese character identity.  A close
    bitmap is useful for choosing captures to inspect, but only source/write
    provenance may promote it to a confirmed voiced character.
    """
    visible = sorted({
        value for address, value in enumerate(tiles)
        if address % 0x400 < 0x3C0
    })
    result = []
    for tile_id in visible:
        if tile_id in VOICABLE_BASES:
            continue
        signature = patterns.get(f"{tile_id:02X}")
        if not signature:
            continue
        pattern = bytes.fromhex(signature)
        ranked = []
        for base_id, base_character in VOICABLE_BASES.items():
            base_signature = patterns.get(f"{base_id:02X}")
            if not base_signature:
                continue
            ranked.append((pixel_difference(pattern, bytes.fromhex(base_signature)), base_id, base_character, base_signature))
        if not ranked:
            continue
        difference, base_id, base_character, base_signature = min(ranked)
        # A real precomposed voiced glyph should retain much of its base.  Keep
        # this permissive because games may redraw more than the two marks.
        if difference > 24:
            continue
        result.append({
            "status": "shape-candidate",
            "identityConfirmed": False,
            "tileId": tile_id,
            "patternHex": signature,
            "nearestBaseTileId": base_id,
            "nearestBaseCharacter": base_character,
            "nearestBasePatternHex": base_signature,
            "differentPixels": difference,
            "occurrences": visible_occurrences(tiles, tile_id),
        })
    return sorted(result, key=lambda item: (item["differentPixels"], item["tileId"]))


def process_snapshot(event: dict, chr_patterns: dict[str, list[dict]], output: Path) -> dict:
    tiles = bytes.fromhex(event["tilesHex"])
    patterns = event["patterns"]
    used_tile_ids = {
        value for address, value in enumerate(tiles)
        if address % 0x400 < 0x3C0
    }
    comparisons = []
    for tile_hex, signature in sorted(patterns.items()):
        if int(tile_hex, 16) not in used_tile_ids:
            continue
        comparisons.append({
            "tileId": int(tile_hex, 16),
            "ppuPatternHex": signature,
            "sha256": hashlib.sha256(bytes.fromhex(signature)).hexdigest(),
            "perfectChrMatches": chr_patterns.get(signature, []),
        })
    candidates = shape_candidates(tiles, patterns)
    report = {
        "frame": event["frame"],
        "patternBase": event["patternBase"],
        "tileComparisonCount": len(comparisons),
        "allUsedPatternsMatchedChr": all(item["perfectChrMatches"] for item in comparisons),
        "comparisons": comparisons,
        "confirmedVoicingSamples": [],
        "voicingShapeCandidates": candidates,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "latest-nametable-comparison.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    render_nametables(tiles, patterns, output / "latest-nametables.png")
    if candidates:
        best = candidates[0]
        render_dakuten({
            "voicedPatternHex": best["patternHex"],
            "unvoicedPatternHex": best["nearestBasePatternHex"],
        }, output / "latest-voicing-shape-candidate.png")
    else:
        stale = output / "latest-voicing-shape-candidate.png"
        if stale.exists():
            stale.unlink()
    return report


def accumulate_candidates(catalog: dict[str, dict], report: dict, output: Path) -> None:
    for candidate in report["voicingShapeCandidates"]:
        key = "%04X:%02X:%s" % (
            report["patternBase"], candidate["tileId"], candidate["patternHex"]
        )
        saved = catalog.get(key)
        sighting = {
            "frame": report["frame"],
            "occurrences": candidate["occurrences"],
        }
        if saved is None:
            saved = dict(candidate)
            saved["patternBase"] = report["patternBase"]
            saved["sightings"] = []
            catalog[key] = saved
        saved["sightings"].append(sighting)
        saved["sightings"] = saved["sightings"][-20:]
    ordered = sorted(catalog.values(), key=lambda item: (item["differentPixels"], item["tileId"]))
    (output / "session-voicing-candidates.json").write_text(
        json.dumps({
            "warning": "Shape candidates are not character identifications; provenance confirmation is required.",
            "candidateCount": len(ordered),
            "candidates": ordered,
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    render_candidate_sheet(ordered, output / "session-voicing-candidates.png")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesen", type=Path, required=True)
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--script", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    patterns = chr_index(ines_chr(args.rom.read_bytes()))
    candidate_catalog: dict[str, dict] = {}
    confirmed_samples: list[dict] = []
    command = [str(args.mesen), "--enableStdout", "--doNotSaveSettings", str(args.script), str(args.rom)]
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1) as process:
        assert process.stdout is not None
        for line in process.stdout:
            if line.startswith("DQNT "):
                report = process_snapshot(json.loads(line[5:]), patterns, args.output)
                accumulate_candidates(candidate_catalog, report, args.output)
                print(
                    f"Captured frame {report['frame']}: {report['tileComparisonCount']} used tiles; "
                    f"voicing shape candidates={len(report['voicingShapeCandidates'])}; "
                    f"all match={report['allUsedPatternsMatchedChr']}",
                    flush=True,
                )
            elif line.startswith("DQVOICE "):
                sample = confirmed_voice_sample(json.loads(line[8:]), patterns)
                confirmed_samples.append(sample)
                save_confirmed_samples(confirmed_samples, args.output)
                print(
                    "Confirmed modifier write: source=%s character=%s tile=$%02X cell=%d:%d,%d" % (
                        "+".join(f"${value:02X}" for value in sample["sourceEncoding"]),
                        sample["logicalCharacter"] or "unknown",
                        sample["tileId"], sample["page"], sample["row"], sample["column"],
                    ), flush=True,
                )
            elif not line.startswith("DQNT_READY"):
                sys.stdout.write(line)
    return process.wait()


if __name__ == "__main__":
    raise SystemExit(main())
