"""Generate a diagnostic that maps dialogue glyphs to Nametable cells."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from .database import DatabaseError, GameDatabase, load_database, validate_rom
from .dialogue_overlay import (
    load_mesen_font_characters,
    shortest_unique_prefix,
    validate_presentation_characters,
)
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


def validate_segments(record: dict[str, Any], glyph_count: int) -> None:
    segments = record.get("segments")
    if not isinstance(segments, list) or not segments:
        raise DatabaseError(f"dialogue segments must be non-empty: {record.get('id')}")
    expected_start = 0
    for index, segment in enumerate(segments):
        if not isinstance(segment, dict):
            raise DatabaseError(f"dialogue segment must be an object: {record.get('id')}")
        start = segment.get("sourceStart")
        end = segment.get("sourceEndExclusive")
        lines = segment.get("lines")
        if start != expected_start or not isinstance(end, int) or end <= start:
            raise DatabaseError(
                f"dialogue segments must be contiguous at segment {index}: "
                f"{record.get('id')}"
            )
        if not isinstance(lines, list) or not lines or not all(
            isinstance(line, str) and line for line in lines
        ):
            raise DatabaseError(f"dialogue segment lines must be non-empty: {record.get('id')}")
        expected_start = end
    if expected_start != glyph_count:
        raise DatabaseError(
            f"dialogue segments must cover {glyph_count} glyphs: {record.get('id')}"
        )


def select_segment(
    segments: list[dict[str, Any]], visible_indices: Iterable[int]
) -> int | None:
    """Select the segment containing the newest currently visible glyph."""
    indices = list(visible_indices)
    if not indices:
        return None
    anchor = max(indices)
    for index, segment in enumerate(segments):
        if segment["sourceStart"] <= anchor < segment["sourceEndExclusive"]:
            return index
    return None


class SubtitleEventRouter:
    """Turn runtime provenance events into renderer-agnostic subtitle state."""

    def __init__(
        self,
        translations: dict[str, Any],
        database: GameDatabase | None = None,
        activation_coverage: float = 0.8,
    ):
        if not 0 < activation_coverage <= 1:
            raise ValueError("activation coverage must be in (0, 1]")
        self._activation_coverage = activation_coverage
        self._records = {
            record["id"]: record for record in translations.get("records", [])
        }
        self._layouts = {
            record.id: record
            for record in (database.records if database else ())
            if record.presentation is not None
        }
        self._visible_layouts: dict[str, int] = {}
        self._layout_order = 0
        self._subtitle_state: dict[str, Any] | None = None
        self._active_segments: dict[str, set[tuple[int, int]]] = {}

    def _layout_state(self) -> dict[str, Any]:
        if not self._visible_layouts:
            return {"visible": False, "mode": "empty", "text": ""}
        record_id = max(self._visible_layouts, key=self._visible_layouts.__getitem__)
        record = self._layouts[record_id]
        assert record.presentation is not None
        return {
            "visible": True,
            "mode": "layout",
            "recordId": record_id,
            "labels": [
                {
                    "text": label.text,
                    "x": label.x / 256.0,
                    "y": label.y / 240.0,
                }
                for label in record.presentation.labels
            ],
        }

    def consume(self, line: str) -> dict[str, Any] | None:
        glyph_marker = "DQGLYPH "
        menu_marker = "DQMENU "
        position = line.find(glyph_marker)
        marker = glyph_marker
        if position < 0:
            position = line.find(menu_marker)
            marker = menu_marker
        if position < 0:
            return None
        try:
            event = json.loads(line[position + len(marker):])
        except json.JSONDecodeError:
            return None
        if marker == menu_marker:
            if event.get("type") != "group" or event.get("recordId") not in self._layouts:
                return None
            record_id = event["recordId"]
            if event.get("cellCount", 0) > 0:
                self._layout_order += 1
                self._visible_layouts[record_id] = self._layout_order
            else:
                self._visible_layouts.pop(record_id, None)
            return None if self._subtitle_state else self._layout_state()
        if event.get("type") == "reset":
            self._subtitle_state = None
            self._active_segments.pop(str(event.get("recordId")), None)
            return self._layout_state()
        if event.get("type") == "coverage":
            record = self._records.get(event.get("recordId"))
            if record is None:
                return None
            active = self._active_segments.setdefault(record["id"], set())
            coverage_by_range = {
                (item.get("sourceStart"), item.get("sourceEndExclusive")): item
                for item in event.get("segments", [])
                if isinstance(item, dict)
            }
            for segment in record.get("segments", []):
                key = (segment["sourceStart"], segment["sourceEndExclusive"])
                item = coverage_by_range.get(key, {})
                visible = int(item.get("visibleCount", 0))
                total = segment["sourceEndExclusive"] - segment["sourceStart"]
                if visible == 0:
                    active.discard(key)
                elif visible / total >= self._activation_coverage:
                    active.add(key)
            lines = [
                line
                for segment in record.get("segments", [])
                if (segment["sourceStart"], segment["sourceEndExclusive"]) in active
                for line in segment["lines"]
            ]
            if not lines:
                if self._subtitle_state is not None:
                    self._subtitle_state = None
                    return self._layout_state()
                return None
            self._subtitle_state = {
                "visible": True,
                "mode": "subtitle",
                "recordId": record["id"],
                "text": "\n".join(lines),
            }
            return self._subtitle_state
        if event.get("type") != "segment":
            return None
        # Retained in the Lua trace for in-frame diagnostics. External
        # presentation is driven by complete visible-coverage snapshots.
        return None


def _lua_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def build_config(
    catalog: dict[str, Any],
    translations: dict[str, Any],
    character_map: dict[int, dict[str, Any]],
    *,
    display_segments: bool = False,
    database: GameDatabase | None = None,
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
        f"local displaySegments = {'true' if display_segments else 'false'}",
        f"local chrStreamSelectorPc = {runtime['chrStreamSelectorPc']}",
        f"local chrWindowSetupPc = {runtime['chrWindowSetupPc']}",
        f"local chrWindowWriterPc = {runtime['chrWindowWriterPc']}",
        f"local scratchFirstAddress = {runtime['scratchFirstAddress']}",
        f"local visibilityStart = {runtime['visibilityStart']}",
        f"local visibilityEndExclusive = {runtime['visibilityEndExclusive']}",
        "local layoutRecords = {",
    ]
    if database is not None:
        for record in database.records:
            if record.presentation is None:
                continue
            lines.append(
                "  { id = %s, startAddress = %d, endAddress = %d },"
                % (
                    _lua_string(record.id),
                    database.cpu_address_base + record.prg_start,
                    database.cpu_address_base + record.prg_end_exclusive - 1,
                )
            )
    lines.extend([
        "}",
        "local records = {",
    ])
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
        validate_segments(translation, len(glyphs))
        box = translation.get("box")
        if not isinstance(box, dict):
            raise DatabaseError(f"dialogue box must be an object: {record_id}")
        lines.extend([
            "  {",
            f"    id = {_lua_string(record_id)},",
            "    matchPrefix = { " + ", ".join(map(str, prefix)) + " },",
            f"    x = {box['x']}, y = {box['y']}, width = {box['width']},",
            f"    height = {box['height']}, lineHeight = {box['lineHeight']},",
            "    segments = {",
        ])
        for segment in translation["segments"]:
            lines.append("      { sourceStart = %d, sourceEndExclusive = %d, lines = { %s } }," % (
                segment["sourceStart"], segment["sourceEndExclusive"],
                ", ".join(_lua_string(line) for line in segment["lines"]),
            ))
        lines.extend([
            "    },",
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
    *,
    display_segments: bool = False,
    database: GameDatabase | None = None,
) -> str:
    if template.count(CONFIG_MARKER) != 1:
        raise ValueError("glyph provenance template must contain exactly one config marker")
    return template.replace(
        CONFIG_MARKER,
        build_config(
            catalog,
            translations,
            character_map,
            display_segments=display_segments,
            database=database,
        ),
    )


def run(
    mesen: Path,
    template_path: Path,
    rom_path: Path,
    database_path: Path,
    catalog_path: Path,
    translations_path: Path,
    character_map_path: Path,
    display_segments: bool,
    font_source_path: Path | None,
    external_subtitles: bool,
    subtitle_companion_path: Path | None,
) -> int:
    if display_segments and external_subtitles:
        raise ValueError("choose either in-game or external segment display")
    database = load_database(database_path)
    validate_rom(database, rom_path)
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    if catalog.get("romSha256") != database.rom_sha256:
        raise DatabaseError("dialogue catalog does not match the bound ROM")
    translations = json.loads(translations_path.read_text(encoding="utf-8"))
    if display_segments and font_source_path is not None:
        validate_presentation_characters(
            translations, load_mesen_font_characters(font_source_path)
        )
    script = build_script(
        catalog,
        translations,
        load_character_map(character_map_path),
        template_path.read_text(encoding="utf-8"),
        display_segments=display_segments,
        database=database,
    )
    with tempfile.TemporaryDirectory(prefix="nes-dialogue-glyph-provenance-") as folder:
        generated = Path(folder) / "dialogue-glyph-provenance.lua"
        generated.write_text(script, encoding="utf-8")
        print("Starting dialogue glyph provenance diagnostic...", flush=True)
        command = [
            str(mesen), "--enableStdout", "--doNotSaveSettings",
            str(generated), str(rom_path),
        ]
        if not external_subtitles:
            with subprocess.Popen(command) as process:
                return process.wait()

        if subtitle_companion_path is None:
            raise ValueError("external subtitles require a companion path")
        router = SubtitleEventRouter(translations, database)
        with subprocess.Popen(
            ["/usr/bin/python3", str(subtitle_companion_path)],
            stdin=subprocess.PIPE,
            text=True,
        ) as companion, subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        ) as process:
            assert process.stdout is not None
            assert companion.stdin is not None
            for line in process.stdout:
                sys.stdout.write(line)
                sys.stdout.flush()
                state = router.consume(line)
                if state is not None and companion.poll() is None:
                    companion.stdin.write(json.dumps(state, ensure_ascii=False) + "\n")
                    companion.stdin.flush()
            companion.stdin.close()
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
    parser.add_argument("--display-segments", action="store_true")
    parser.add_argument("--font-source", type=Path)
    parser.add_argument("--external-subtitles", action="store_true")
    parser.add_argument("--subtitle-companion", type=Path)
    args = parser.parse_args()
    raise SystemExit(run(
        args.mesen, args.template, args.rom, args.game_database, args.catalog,
        args.translations, args.character_map,
        args.display_segments, args.font_source,
        args.external_subtitles, args.subtitle_companion,
    ))


if __name__ == "__main__":
    main()
