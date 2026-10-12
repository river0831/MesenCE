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


@dataclass(frozen=True)
class PpuBounds:
    """A renderer-independent rectangle in the NES 256x240 viewport."""

    x: int
    y: int
    width: int
    height: int

    def as_dict(self) -> dict[str, int]:
        return asdict(self)


@dataclass(frozen=True)
class TextUnit:
    """One independently visible translation, regardless of its source kind."""

    id: str
    record_id: str
    text: str
    ppu_bounds: PpuBounds
    total_count: int
    font_size: float
    source_start: int | None = None
    source_end_exclusive: int | None = None
    line_count: int = 1
    line_height: int | None = None

    def snapshot_item(
        self, visible_count: int, ppu_bounds: PpuBounds | None = None
    ) -> dict[str, Any]:
        item: dict[str, Any] = {
            "unitId": self.id,
            "recordId": self.record_id,
            "text": self.text,
            "ppuBounds": (ppu_bounds or self.ppu_bounds).as_dict(),
            "visibleCount": visible_count,
            "totalCount": self.total_count,
            "visibleRatio": min(visible_count / self.total_count, 1.0),
            "fontSize": self.font_size,
        }
        if self.source_start is not None:
            item["sourceStart"] = self.source_start
        if self.source_end_exclusive is not None:
            item["sourceEndExclusive"] = self.source_end_exclusive
        return item


def build_text_units(
    translations: dict[str, Any], database: GameDatabase | None = None
) -> tuple[TextUnit, ...]:
    """Normalize menu labels and dialogue segments into one read model."""
    units: list[TextUnit] = []
    for record in database.records if database else ():
        if record.presentation is None:
            continue
        for index, label in enumerate(record.presentation.labels, 1):
            total = (
                ((label.clear.width + 7) // 8)
                * ((label.clear.height + 7) // 8)
            )
            units.append(TextUnit(
                id=f"{record.id}#label-{index}",
                record_id=record.id,
                text=label.text,
                ppu_bounds=PpuBounds(
                    label.clear.x, label.clear.y,
                    label.clear.width, label.clear.height,
                ),
                total_count=total,
                font_size=7.5,
            ))
    for record in translations.get("records", []):
        box = record["box"]
        for segment in record.get("segments", []):
            start = segment["sourceStart"]
            end = segment["sourceEndExclusive"]
            lines = segment["lines"]
            units.append(TextUnit(
                id=f"{record['id']}#glyph-{start}-{end}",
                record_id=record["id"],
                text="\n".join(lines),
                ppu_bounds=PpuBounds(
                    box["x"], box["y"], box["width"], box["height"]
                ),
                total_count=end - start,
                font_size=8.5,
                source_start=start,
                source_end_exclusive=end,
                line_count=len(lines),
                line_height=box["lineHeight"],
            ))
    ids = [unit.id for unit in units]
    if len(ids) != len(set(ids)):
        raise DatabaseError("duplicate normalized text unit id")
    return tuple(units)


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
    """Project current Nametable provenance into a renderer-agnostic scene."""

    def __init__(
        self,
        translations: dict[str, Any],
        database: GameDatabase | None = None,
        activation_coverage: float = 0.25,
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
        units = build_text_units(translations, database)
        self._layout_units = {
            (unit.record_id, int(unit.id.rsplit("-", 1)[1])): unit
            for unit in units if "#label-" in unit.id
        }
        self._dialogue_units = {
            (unit.record_id, unit.source_start, unit.source_end_exclusive): unit
            for unit in units if unit.source_start is not None
        }
        self._visible_layouts: dict[str, dict[int, int]] = {}
        self._visible_dialogue: dict[str, list[dict[str, Any]]] = {}
        self._frame = 0

    def _scene_state(self) -> dict[str, Any]:
        items = []
        for record_id in sorted(self._visible_layouts):
            visible_labels = self._visible_layouts[record_id]
            for index in sorted(visible_labels):
                unit = self._layout_units[(record_id, index)]
                items.append(unit.snapshot_item(visible_labels[index]))
        for record_id in sorted(self._visible_dialogue):
            segments = self._visible_dialogue[record_id]
            units = [
                self._dialogue_units[(
                    record_id, segment["sourceStart"],
                    segment["sourceEndExclusive"],
                )]
                for segment in segments
            ]
            box = units[0].ppu_bounds
            total_height = sum(
                unit.line_count * (unit.line_height or 0) for unit in units
            )
            next_y = box.y + max((box.height - total_height) // 2, 0)
            for unit, segment in zip(units, segments):
                item_height = unit.line_count * (unit.line_height or 0)
                bounds = PpuBounds(box.x, next_y, box.width, item_height)
                items.append(unit.snapshot_item(segment["visibleCount"], bounds))
                next_y += item_height
        return {
            "frame": self._frame,
            "visible": bool(items),
            "mode": "visible-translation-snapshot",
            "items": items,
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
        if isinstance(event.get("frame"), int):
            self._frame = event["frame"]
        if marker == menu_marker:
            if event.get("type") != "group" or event.get("recordId") not in self._layouts:
                return None
            record_id = event["recordId"]
            label_counts = event.get("labels")
            if isinstance(label_counts, list):
                visible = {
                    int(item["index"]): int(item.get("cellCount", 0))
                    for item in label_counts
                    if isinstance(item, dict)
                    and isinstance(item.get("index"), int)
                    and int(item.get("cellCount", 0)) > 0
                }
            elif event.get("cellCount", 0) > 0:
                presentation = self._layouts[record_id].presentation
                assert presentation is not None
                visible = {
                    index: (
                        ((label.clear.width + 7) // 8)
                        * ((label.clear.height + 7) // 8)
                    )
                    for index, label in enumerate(presentation.labels, 1)
                }
            else:
                visible = set()
            if visible:
                self._visible_layouts[record_id] = visible
            else:
                self._visible_layouts.pop(record_id, None)
            return self._scene_state()
        if event.get("type") == "reset":
            self._visible_dialogue.pop(str(event.get("recordId")), None)
            return self._scene_state()
        if event.get("type") == "coverage":
            record = self._records.get(event.get("recordId"))
            if record is None:
                return None
            coverage_by_range = {
                (item.get("sourceStart"), item.get("sourceEndExclusive")): item
                for item in event.get("segments", [])
                if isinstance(item, dict)
            }
            visible_segments = []
            for segment in record.get("segments", []):
                key = (segment["sourceStart"], segment["sourceEndExclusive"])
                item = coverage_by_range.get(key, {})
                visible = int(item.get("visibleCount", 0))
                total = segment["sourceEndExclusive"] - segment["sourceStart"]
                if total > 0 and visible / total >= self._activation_coverage:
                    visible_segments.append({
                        **segment,
                        "visibleCount": visible,
                        "totalCount": total,
                        "visibleRatio": visible / total,
                    })
            if visible_segments:
                self._visible_dialogue[record["id"]] = visible_segments
            else:
                self._visible_dialogue.pop(record["id"], None)
            return self._scene_state()
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
            lines.extend([
                "  { id = %s, startAddress = %d, endAddress = %d, labels = {"
                % (
                    _lua_string(record.id),
                    database.cpu_address_base + record.prg_start,
                    database.cpu_address_base + record.prg_end_exclusive - 1,
                ),
            ])
            for index, label in enumerate(record.presentation.labels, 1):
                start_x = label.clear.x
                start_y = label.clear.y
                end_x = label.clear.x + label.clear.width
                end_y = label.clear.y + label.clear.height
                lines.append(
                    "    { index = %d, startX = %d, endX = %d, "
                    "startY = %d, endY = %d },"
                    % (index, start_x, end_x, start_y, end_y)
                )
            lines.extend(["  } },"])
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
