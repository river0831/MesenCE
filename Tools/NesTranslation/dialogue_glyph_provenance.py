"""Generate a diagnostic that maps dialogue glyphs to Nametable cells."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from .database import DatabaseError, load_database, validate_rom
from .dialogue_overlay import shortest_unique_prefix
from .text_review import load_character_map


CONFIG_MARKER = "-- __NES_TRANSLATION_GLYPH_PROVENANCE_CONFIG__"


@dataclass(frozen=True)
class LogicalGlyph:
    index: int
    value: int
    display: str
    expanded_index: int
    source_offset: int


def logical_glyphs(
    record: dict[str, Any], character_map: dict[int, dict[str, Any]]
) -> tuple[LogicalGlyph, ...]:
    """Flatten a catalog record while excluding controls and modifiers.

    A modifier such as dakuten belongs to the preceding logical glyph and does
    not advance the source position. Unknown/control bytes remain present in
    the catalog, but are deliberately not guessed to be visible glyphs here.
    """
    result: list[LogicalGlyph] = []
    expanded_index = 0
    for token in record.get("tokens", []):
        for value in token.get("expanded", []):
            entry = character_map.get(value)
            if entry is not None and entry.get("type") == "glyph":
                result.append(LogicalGlyph(
                    index=len(result),
                    value=value,
                    display=str(entry.get("display", "")),
                    expanded_index=expanded_index,
                    source_offset=int(token["source_offset"]),
                ))
            expanded_index += 1
    return tuple(result)


def group_visible_cells(
    cells: Iterable[tuple[int, str, int]], width: int = 32
) -> list[dict[str, Any]]:
    """Group (Nametable address, record id, glyph index) cells by row."""
    if width <= 0:
        raise ValueError("Nametable width must be positive")
    rows: dict[tuple[str, int], list[tuple[int, int]]] = {}
    for address, record_id, glyph_index in cells:
        row, column = divmod(address % 0x400, width)
        rows.setdefault((record_id, row), []).append((column, glyph_index))
    result = []
    for (record_id, row), values in sorted(rows.items()):
        values.sort()
        indices = [item[1] for item in values]
        result.append({
            "recordId": record_id,
            "row": row,
            "columns": [item[0] for item in values],
            "start": min(indices),
            "endExclusive": max(indices) + 1,
            "cellCount": len(values),
        })
    return result


def _lua_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def build_config(
    catalog: dict[str, Any],
    translations: dict[str, Any],
    character_map: dict[int, dict[str, Any]],
) -> str:
    records_by_id = {record["id"]: record for record in catalog.get("records", [])}
    all_raw = [bytes.fromhex(record["rawHex"]) for record in catalog.get("records", [])]
    runtime = translations.get("runtime")
    if not isinstance(runtime, dict):
        raise DatabaseError("dialogue translation runtime must be an object")

    required = (
        "chrStreamSelectorPc", "chrWindowSetupPc", "chrWindowWriterPc",
        "scratchFirstAddress", "visibilityStart", "visibilityEndExclusive",
    )
    for key in required:
        if not isinstance(runtime.get(key), int) or runtime[key] < 0:
            raise DatabaseError(f"dialogue runtime.{key} must be non-negative")

    lines = [
        f"local chrStreamSelectorPc = {runtime['chrStreamSelectorPc']}",
        f"local chrWindowSetupPc = {runtime['chrWindowSetupPc']}",
        f"local chrWindowWriterPc = {runtime['chrWindowWriterPc']}",
        f"local scratchFirstAddress = {runtime['scratchFirstAddress']}",
        f"local visibilityStart = {runtime['visibilityStart']}",
        f"local visibilityEndExclusive = {runtime['visibilityEndExclusive']}",
        "local records = {",
    ]
    for translation in translations.get("records", []):
        record_id = translation.get("id")
        record = records_by_id.get(record_id)
        if record is None:
            raise DatabaseError(f"translation references unknown catalog record: {record_id}")
        if record.get("runtime", {}).get("status") != "runtime-confirmed":
            raise DatabaseError(f"dialogue record is not runtime-confirmed: {record_id}")
        raw = bytes.fromhex(record["rawHex"])
        prefix = shortest_unique_prefix(raw, all_raw)
        glyphs = logical_glyphs(record, character_map)
        if not glyphs:
            raise DatabaseError(f"dialogue record has no logical glyphs: {record_id}")
        lines.extend([
            "  {",
            f"    id = {_lua_string(record_id)},",
            "    matchPrefix = { " + ", ".join(map(str, prefix)) + " },",
            "    glyphs = {",
        ])
        for glyph in glyphs:
            lines.append(
                "      { index = %d, value = %d, sourceOffset = %d, "
                "expandedIndex = %d },"
                % (glyph.index, glyph.value, glyph.source_offset, glyph.expanded_index)
            )
        lines.extend(["    },", "  },"])
    lines.append("}")
    return "\n".join(lines)


def build_script(
    catalog: dict[str, Any],
    translations: dict[str, Any],
    character_map: dict[int, dict[str, Any]],
    template: str,
) -> str:
    if template.count(CONFIG_MARKER) != 1:
        raise ValueError("glyph provenance template must contain exactly one config marker")
    return template.replace(
        CONFIG_MARKER, build_config(catalog, translations, character_map)
    )


def run(
    mesen: Path,
    template_path: Path,
    rom_path: Path,
    database_path: Path,
    catalog_path: Path,
    translations_path: Path,
    character_map_path: Path,
) -> int:
    database = load_database(database_path)
    validate_rom(database, rom_path)
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    if catalog.get("romSha256") != database.rom_sha256:
        raise DatabaseError("dialogue catalog does not match the bound ROM")
    translations = json.loads(translations_path.read_text(encoding="utf-8"))
    script = build_script(
        catalog,
        translations,
        load_character_map(character_map_path),
        template_path.read_text(encoding="utf-8"),
    )
    with tempfile.TemporaryDirectory(prefix="nes-dialogue-glyph-provenance-") as folder:
        generated = Path(folder) / "dialogue-glyph-provenance.lua"
        generated.write_text(script, encoding="utf-8")
        print("Starting dialogue glyph provenance diagnostic...", flush=True)
        with subprocess.Popen([
            str(mesen), "--enableStdout", "--doNotSaveSettings",
            str(generated), str(rom_path),
        ]) as process:
            return process.wait()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesen", required=True, type=Path)
    parser.add_argument("--template", required=True, type=Path)
    parser.add_argument("--rom", required=True, type=Path)
    parser.add_argument("--game-database", required=True, type=Path)
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--translations", required=True, type=Path)
    parser.add_argument("--character-map", required=True, type=Path)
    args = parser.parse_args()
    raise SystemExit(run(
        args.mesen, args.template, args.rom, args.game_database, args.catalog,
        args.translations, args.character_map,
    ))


if __name__ == "__main__":
    main()
