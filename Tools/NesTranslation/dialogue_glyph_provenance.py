"""Generate a diagnostic that maps dialogue glyphs to Nametable cells."""

from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .database import DatabaseError, GameDatabase, load_database, validate_rom
from .dictionary_catalog import validate_vocabulary
from .dialogue_overlay import (
    load_mesen_font_characters,
    shortest_unique_prefix,
    validate_presentation_characters,
)
from .text_review import load_character_map
from .text_units import PpuBounds, TextUnit, VisibilityUpdate, build_text_units


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


@dataclass(frozen=True)
class VisibleLexeme:
    id: str
    pattern: tuple[int, ...]
    display: str
    category: str
    row: int
    column: int


class NametableTextComposer:
    """Compose messages solely from text that is currently visible in PPU RAM."""

    _MODIFIERS = frozenset((0xF8, 0xF9))

    def __init__(self, vocabulary: dict[str, Any], catalog: dict[str, Any]):
        entries = {entry["id"]: entry for entry in catalog.get("entries", [])}
        self._lexemes: list[dict[str, Any]] = []
        self._actions: list[dict[str, Any]] = []
        for record in vocabulary.get("records", []):
            entry = entries.get(record.get("id"))
            if entry is None:
                continue
            candidate = dict(record)
            candidate["pattern"] = self._normalize(bytes.fromhex(entry["rawHex"]))
            self._lexemes.append(candidate)
            if isinstance(candidate.get("composition"), dict):
                self._actions.append(candidate)
        for record in vocabulary.get("ppuLexemes", []):
            candidate = dict(record)
            candidate["pattern"] = self._normalize(
                bytes.fromhex(candidate["sourceHex"])
            )
            self._lexemes.append(candidate)

    @classmethod
    def _normalize(cls, values: Iterable[int]) -> tuple[int, ...]:
        return tuple(value for value in values if value not in cls._MODIFIERS)

    @staticmethod
    def _find(row: tuple[int, ...], pattern: tuple[int, ...]) -> list[int]:
        if not pattern:
            return []
        return [
            column for column in range(len(row) - len(pattern) + 1)
            if row[column:column + len(pattern)] == pattern
        ]

    def _visible(self, rows: list[tuple[int, ...]]) -> list[VisibleLexeme]:
        result = []
        for record in self._lexemes:
            pattern = record["pattern"]
            for row_index, row in enumerate(rows):
                for column in self._find(row, pattern):
                    result.append(VisibleLexeme(
                        id=record["id"], pattern=pattern,
                        display=record["display"], category=record["category"],
                        row=row_index, column=column,
                    ))
        return result

    @staticmethod
    def _amount_before(rows: list[tuple[int, ...]], lexeme: VisibleLexeme) -> str:
        digits = []
        column = lexeme.column - 1
        while column >= 0 and 0 <= rows[lexeme.row][column] <= 9:
            digits.append(str(rows[lexeme.row][column]))
            column -= 1
        amount = "".join(reversed(digits)).lstrip("0")
        return amount or ("0" if digits else "")

    def compose(self, encoded_rows: list[dict[str, Any]]) -> dict[str, Any] | None:
        rows_by_index: dict[int, tuple[int, ...]] = {}
        for item in encoded_rows:
            if not isinstance(item, dict) or not isinstance(item.get("row"), int):
                continue
            try:
                row = tuple(bytes.fromhex(str(item.get("hex", ""))))
            except ValueError:
                continue
            if len(row) == 32:
                rows_by_index[item["row"]] = row
        if len(rows_by_index) != 30:
            return None
        rows = [rows_by_index[index] for index in range(30)]
        visible = self._visible(rows)
        by_id = {record["id"]: record for record in self._actions}
        actions = [item for item in visible if item.id in by_id]
        for action in sorted(actions, key=lambda item: (item.row, item.column), reverse=True):
            spec = by_id[action.id]["composition"]
            categories = set(spec.get("objectCategories", []))
            objects = [
                item for item in visible
                if item.category in categories
                and 0 <= action.row - item.row <= int(spec.get("maxRowDistance", 3))
            ]
            if categories and not objects:
                continue
            object_lexeme = min(
                objects,
                key=lambda item: (action.row - item.row, abs(action.column - item.column)),
                default=None,
            )
            amount = (
                self._amount_before(rows, object_lexeme)
                if object_lexeme is not None and spec.get("captureAmount") else ""
            )
            if spec.get("captureAmount") and not amount:
                continue
            text = str(spec["format"])
            text = text.replace("{object}", object_lexeme.display if object_lexeme else "")
            text = text.replace("{amount}", amount)
            matches = [action] + ([object_lexeme] if object_lexeme else [])
            left = min(item.column for item in matches)
            right = max(item.column + len(item.pattern) for item in matches)
            top = min(item.row for item in matches)
            bottom = max(item.row for item in matches) + 1
            return {
                "unitId": "ppu-message:" + action.id,
                "recordId": action.id,
                "text": text,
                "ppuBounds": {
                    "x": left * 8, "y": top * 8,
                    "width": (right - left) * 8, "height": (bottom - top) * 8,
                },
                "visibleCount": sum(len(item.pattern) for item in matches),
                "totalCount": sum(len(item.pattern) for item in matches),
                "visibleRatio": 1.0,
                "fontSize": 8.5,
            }
        return None


class SubtitleEventRouter:
    """Project current Nametable provenance into a renderer-agnostic scene."""

    def __init__(
        self,
        translations: dict[str, Any],
        database: GameDatabase | None = None,
        vocabulary: dict[str, Any] | None = None,
        dictionary_catalog: dict[str, Any] | None = None,
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
        units = build_text_units(translations, database, vocabulary)
        self._units_by_id = {unit.id: unit for unit in units}
        self._layout_units = {
            (unit.record_id, unit.source_index): unit
            for unit in units if unit.kind == "label"
        }
        self._vocabulary_units = {
            unit.record_id: unit for unit in units if unit.kind == "vocabulary"
        }
        self._nametable_composer = NametableTextComposer(
            vocabulary or {}, dictionary_catalog or {}
        )
        self._composed_item: dict[str, Any] | None = None
        self._dialogue_units = {
            (unit.record_id, unit.source_start, unit.source_end_exclusive): unit
            for unit in units if unit.kind == "dialogue"
        }
        self._visible_units: dict[str, int] = {}
        self._visible_bounds: dict[str, PpuBounds] = {}
        self._scope_units = {
            f"{unit.kind}:{unit.record_id}": {
                candidate.id for candidate in units
                if candidate.kind == unit.kind
                and candidate.record_id == unit.record_id
            }
            for unit in units
        }
        self._last_snapshot_items: dict[str, dict[str, Any]] = {}
        self._frame = 0

    def apply_visibility(self, update: VisibilityUpdate) -> dict[str, Any]:
        """Replace one source scope with its complete current visible state."""
        scope_units = self._scope_units.get(update.scope_id)
        if scope_units is None:
            raise ValueError(f"unknown visibility scope: {update.scope_id}")
        counts = dict(update.unit_counts)
        unknown = counts.keys() - scope_units
        if unknown:
            raise ValueError(
                f"visibility update contains units outside scope: {sorted(unknown)}"
            )
        for unit_id in scope_units:
            self._visible_units.pop(unit_id, None)
            self._visible_bounds.pop(unit_id, None)
        incoming_dialogue = [
            self._units_by_id[unit_id]
            for unit_id in counts
            if self._units_by_id[unit_id].kind == "dialogue"
        ]
        if incoming_dialogue:
            incoming_boxes = [unit.ppu_bounds for unit in incoming_dialogue]
            for unit_id in tuple(self._visible_units):
                visible = self._units_by_id[unit_id]
                if (
                    visible.kind == "dialogue"
                    and visible.record_id != incoming_dialogue[0].record_id
                    and any(
                        self._bounds_overlap(visible.ppu_bounds, box)
                        for box in incoming_boxes
                    )
                ):
                    self._visible_units.pop(unit_id, None)
                    self._visible_bounds.pop(unit_id, None)
        self._visible_units.update(counts)
        self._visible_bounds.update(dict(update.unit_bounds))
        return self._scene_state()

    @staticmethod
    def _bounds_overlap(first: PpuBounds, second: PpuBounds) -> bool:
        return (
            first.x < second.x + second.width
            and second.x < first.x + first.width
            and first.y < second.y + second.height
            and second.y < first.y + first.height
        )

    @staticmethod
    def _fit_dialogue_units(
        units: list[TextUnit], available_height: int
    ) -> list[TextUnit]:
        """Keep the newest visible suffix that fits the current PPU box."""
        fitted: list[TextUnit] = []
        used_height = 0
        for unit in reversed(units):
            item_height = unit.line_count * (unit.line_height or 0)
            if fitted and used_height + item_height > available_height:
                break
            fitted.append(unit)
            used_height += item_height
            if used_height >= available_height:
                break
        return list(reversed(fitted))

    def _scene_state(self) -> dict[str, Any]:
        items = []
        dialogue_visible = self._composed_item is not None or any(
            self._units_by_id[unit_id].kind == "dialogue"
            for unit_id in self._visible_units
        )
        layout_units = sorted(
            (
                self._units_by_id[unit_id]
                for unit_id in self._visible_units
                if self._units_by_id[unit_id].kind in ("label", "vocabulary")
                and not (
                    dialogue_visible
                    and self._units_by_id[unit_id].kind == "vocabulary"
                )
            ),
            key=lambda unit: unit.id,
        )
        for unit in layout_units:
            items.append(unit.snapshot_item(
                self._visible_units[unit.id], self._visible_bounds.get(unit.id)
            ))

        dialogue_by_record: dict[str, list[TextUnit]] = {}
        for unit_id in self._visible_units:
            unit = self._units_by_id[unit_id]
            if unit.kind == "dialogue":
                dialogue_by_record.setdefault(unit.record_id, []).append(unit)
        for record_id in sorted(dialogue_by_record):
            units = sorted(
                dialogue_by_record[record_id],
                key=lambda unit: unit.source_start or 0,
            )
            box = units[0].ppu_bounds
            if self._composed_item is not None:
                bounds = self._composed_item["ppuBounds"]
                composed_box = PpuBounds(
                    bounds["x"], bounds["y"], bounds["width"], bounds["height"]
                )
                if self._bounds_overlap(box, composed_box):
                    continue
            units = self._fit_dialogue_units(units, box.height)
            total_height = sum(
                unit.line_count * (unit.line_height or 0) for unit in units
            )
            next_y = box.y + max((box.height - total_height) // 2, 0)
            for unit in units:
                item_height = unit.line_count * (unit.line_height or 0)
                bounds = PpuBounds(box.x, next_y, box.width, item_height)
                items.append(unit.snapshot_item(self._visible_units[unit.id], bounds))
                next_y += item_height
        if self._composed_item is not None:
            items.append(self._composed_item)
        current_items = {item["unitId"]: item for item in items}
        appeared = sorted(current_items.keys() - self._last_snapshot_items.keys())
        disappeared = sorted(self._last_snapshot_items.keys() - current_items.keys())
        updated = sorted(
            unit_id
            for unit_id in current_items.keys() & self._last_snapshot_items.keys()
            if current_items[unit_id] != self._last_snapshot_items[unit_id]
        )
        self._last_snapshot_items = current_items
        return {
            "frame": self._frame,
            "visible": bool(items),
            "mode": "visible-translation-snapshot",
            "items": items,
            "delta": {
                "appeared": appeared,
                "updated": updated,
                "disappeared": disappeared,
            },
        }

    def consume(self, line: str) -> dict[str, Any] | None:
        glyph_marker = "DQGLYPH "
        menu_marker = "DQMENU "
        ppu_marker = "DQPPU "
        position = line.find(glyph_marker)
        marker = glyph_marker
        if position < 0:
            position = line.find(menu_marker)
            marker = menu_marker
        if position < 0:
            position = line.find(ppu_marker)
            marker = ppu_marker
        if position < 0:
            return None
        try:
            event = json.loads(line[position + len(marker):])
        except json.JSONDecodeError:
            return None
        if isinstance(event.get("frame"), int):
            self._frame = event["frame"]
        if marker == ppu_marker:
            if event.get("type") != "nametable":
                return None
            rows = event.get("rows")
            if not isinstance(rows, list):
                return None
            composed_item = self._nametable_composer.compose(rows)
            if composed_item == self._composed_item:
                return None
            self._composed_item = composed_item
            return self._scene_state()
        if marker == menu_marker:
            if event.get("type") != "group":
                return None
            record_id = event["recordId"]
            vocabulary_unit = self._vocabulary_units.get(record_id)
            if record_id not in self._layouts and vocabulary_unit is None:
                return None
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
                visible = {}
            unit_counts = []
            unit_bounds = []
            for index, count in visible.items():
                unit = (
                    vocabulary_unit if vocabulary_unit is not None and index == 1
                    else self._layout_units.get((record_id, index))
                )
                if unit is not None:
                    unit_counts.append((unit.id, count))
                    item = next((
                        candidate for candidate in (label_counts or [])
                        if isinstance(candidate, dict) and candidate.get("index") == index
                    ), None)
                    if item is not None and all(
                        isinstance(item.get(key), int)
                        for key in ("x", "y", "width", "height")
                    ):
                        unit_bounds.append((unit.id, PpuBounds(
                            item["x"], item["y"], item["width"], item["height"]
                        )))
            return self.apply_visibility(VisibilityUpdate(
                scope_id=(
                    f"vocabulary:{record_id}" if vocabulary_unit is not None
                    else f"label:{record_id}"
                ),
                unit_counts=tuple(unit_counts),
                unit_bounds=tuple(unit_bounds),
            ))
        if event.get("type") == "reset":
            record_id = str(event.get("recordId"))
            scope_id = f"dialogue:{record_id}"
            if scope_id not in self._scope_units:
                return None
            return self.apply_visibility(VisibilityUpdate(scope_id, ()))
        if event.get("type") == "record":
            return None
        if event.get("type") == "coverage":
            record = self._records.get(event.get("recordId"))
            if record is None:
                return None
            coverage_by_range = {
                (item.get("sourceStart"), item.get("sourceEndExclusive")): item
                for item in event.get("segments", [])
                if isinstance(item, dict)
            }
            unit_counts = []
            for segment in record.get("segments", []):
                key = (segment["sourceStart"], segment["sourceEndExclusive"])
                item = coverage_by_range.get(key, {})
                visible = int(item.get("visibleCount", 0))
                total = segment["sourceEndExclusive"] - segment["sourceStart"]
                if total > 0 and visible / total >= self._activation_coverage:
                    unit = self._dialogue_units[(record["id"], *key)]
                    unit_counts.append((unit.id, visible))
            return self.apply_visibility(VisibilityUpdate(
                scope_id=f"dialogue:{record['id']}",
                unit_counts=tuple(unit_counts),
            ))

def _lua_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def build_config(
    catalog: dict[str, Any],
    translations: dict[str, Any],
    character_map: dict[int, dict[str, Any]],
    *,
    display_segments: bool = False,
    database: GameDatabase | None = None,
    dictionary_catalog: dict[str, Any] | None = None,
    vocabulary: dict[str, Any] | None = None,
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
        if dictionary_catalog is not None and vocabulary is not None:
            validate_vocabulary(dictionary_catalog, vocabulary)
            entries = {
                entry["id"]: entry for entry in dictionary_catalog.get("entries", [])
            }
            for word in vocabulary.get("records", []):
                entry = entries[word["id"]]
                if entry["prgEndExclusive"] <= entry["prgStart"]:
                    continue
                lines.append(
                    "  { id = %s, startAddress = %d, endAddress = %d, "
                    "dynamic = true, "
                    "labels = {} },"
                    % (
                        _lua_string(word["id"]),
                        database.cpu_address_base + entry["prgStart"],
                        database.cpu_address_base + entry["prgEndExclusive"] - 1,
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
    dictionary_catalog: dict[str, Any] | None = None,
    vocabulary: dict[str, Any] | None = None,
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
            dictionary_catalog=dictionary_catalog,
            vocabulary=vocabulary,
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
    snapshot_trace_path: Path | None = None,
    dictionary_catalog_path: Path | None = None,
    vocabulary_path: Path | None = None,
) -> int:
    if display_segments and external_subtitles:
        raise ValueError("choose either in-game or external segment display")
    database = load_database(database_path)
    validate_rom(database, rom_path)
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    if catalog.get("romSha256") != database.rom_sha256:
        raise DatabaseError("dialogue catalog does not match the bound ROM")
    translations = json.loads(translations_path.read_text(encoding="utf-8"))
    if (dictionary_catalog_path is None) != (vocabulary_path is None):
        raise ValueError("dictionary catalog and vocabulary must be provided together")
    dictionary_catalog = (
        json.loads(dictionary_catalog_path.read_text(encoding="utf-8"))
        if dictionary_catalog_path is not None else None
    )
    vocabulary = (
        json.loads(vocabulary_path.read_text(encoding="utf-8"))
        if vocabulary_path is not None else None
    )
    if dictionary_catalog is not None:
        if dictionary_catalog.get("romSha256") != database.rom_sha256:
            raise DatabaseError("dictionary catalog does not match the bound ROM")
        assert vocabulary is not None
        validate_vocabulary(dictionary_catalog, vocabulary)
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
        dictionary_catalog=dictionary_catalog,
        vocabulary=vocabulary,
    )
    with tempfile.TemporaryDirectory(prefix="nes-dialogue-glyph-provenance-") as folder:
        generated = Path(folder) / "dialogue-glyph-provenance.lua"
        generated.write_text(script, encoding="utf-8")
        print("Starting dialogue glyph provenance diagnostic...", flush=True)
        command = [
            str(mesen), "--enableStdout", "--doNotSaveSettings",
            str(generated), str(rom_path),
        ]
        if not external_subtitles and snapshot_trace_path is None:
            with subprocess.Popen(command) as process:
                return process.wait()

        if external_subtitles and subtitle_companion_path is None:
            raise ValueError("external subtitles require a companion path")
        router = SubtitleEventRouter(
            translations, database, vocabulary, dictionary_catalog=dictionary_catalog
        )
        if snapshot_trace_path is not None:
            snapshot_trace_path.parent.mkdir(parents=True, exist_ok=True)
        with ExitStack() as stack:
            companion = None
            if external_subtitles:
                companion = stack.enter_context(subprocess.Popen(
                    ["/usr/bin/python3", str(subtitle_companion_path)],
                    stdin=subprocess.PIPE,
                    text=True,
                ))
            trace_file = (
                stack.enter_context(snapshot_trace_path.open("w", encoding="utf-8"))
                if snapshot_trace_path is not None else None
            )
            process = stack.enter_context(subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            ))
            assert process.stdout is not None
            for line in process.stdout:
                if "DQPPU " not in line:
                    sys.stdout.write(line)
                    sys.stdout.flush()
                state = router.consume(line)
                if state is None:
                    continue
                serialized = json.dumps(state, ensure_ascii=False)
                if trace_file is not None:
                    trace_file.write(serialized + "\n")
                    trace_file.flush()
                if companion is not None and companion.poll() is None:
                    assert companion.stdin is not None
                    companion.stdin.write(serialized + "\n")
                    companion.stdin.flush()
            if companion is not None and companion.stdin is not None:
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
    parser.add_argument("--dictionary-catalog", type=Path)
    parser.add_argument("--vocabulary", type=Path)
    parser.add_argument(
        "--snapshot-trace", type=Path,
        help="write renderer-independent translation snapshots as JSONL",
    )
    args = parser.parse_args()
    raise SystemExit(run(
        args.mesen, args.template, args.rom, args.game_database, args.catalog,
        args.translations, args.character_map,
        args.display_segments, args.font_source,
        args.external_subtitles, args.subtitle_companion,
        args.snapshot_trace,
        args.dictionary_catalog, args.vocabulary,
    ))


if __name__ == "__main__":
    main()
