"""Incremental shadow state for Nametable text-row write events."""

from __future__ import annotations

from dataclasses import dataclass
from collections import deque
from typing import Any

from .vocabulary import normalize_vocabulary, record_ppu_patterns


@dataclass(frozen=True)
class TextRun:
    row: int
    start_column: int
    values: tuple[int, ...]


@dataclass(frozen=True)
class ScreenCell:
    """One currently known Nametable text cell."""

    row: int
    column: int
    value: int


@dataclass(frozen=True)
class VisualTextRegion:
    """A coarse text-bearing area bounded by known non-text tiles."""

    region_id: str
    top: int
    left: int
    bottom: int
    right: int
    cells: frozenset[tuple[int, int]]
    character_cells: frozenset[tuple[int, int]]


@dataclass(frozen=True)
class TextLine:
    """A conservative same-row sequence of visible text cells."""

    line_id: str
    row: int
    start_column: int
    values: tuple[int, ...]
    cells: tuple[ScreenCell, ...]

    @property
    def end_column(self) -> int:
        return self.start_column + len(self.values)


@dataclass(frozen=True)
class LineSourceMatch:
    """A translation-package source line matching one screen TextLine."""

    line_id: str
    source_unit_id: str
    record_id: str
    source_line_index: int
    source_line_count: int
    score: int
    match_type: str = "ExactLine"
    bindings: tuple[tuple[str, tuple[int, ...]], ...] = ()


@dataclass(frozen=True)
class TextBlockCandidate:
    """A consecutive screen-line group backed by ordered package lines."""

    source_unit_id: str
    record_id: str
    text: str
    lines: tuple[TextLine, ...]
    source_line_start: int
    source_line_end_exclusive: int
    source_line_count: int
    source_start: int | None
    source_end_exclusive: int | None
    score: int
    cells: frozenset[tuple[int, int]]
    match_type: str = "NametableBlock"
    bindings: tuple[tuple[str, tuple[int, ...]], ...] = ()

    @property
    def complete_record(self) -> bool:
        return (
            self.source_line_start == 0
            and self.source_line_end_exclusive == self.source_line_count
        )


@dataclass(frozen=True)
class VisibleTextMatch:
    action_id: str
    text: str
    left: int
    top: int
    right: int
    bottom: int
    object_id: str | None = None
    object_source_text: str | None = None
    object_text: str | None = None
    object_category: str | None = None


@dataclass(frozen=True)
class VisibleLexemeMatch:
    record_id: str
    row: int
    column: int
    length: int


@dataclass(frozen=True)
class VisibleScreenTextMatch:
    source_unit_id: str
    record_id: str
    text: str
    left: int
    top: int
    right: int
    bottom: int
    cells: frozenset[tuple[int, int]]
    match_type: str = "NametableBlock"
    line_count: int = 1
    source_line_start: int = 0
    source_line_end_exclusive: int = 1
    source_start: int | None = None
    source_end_exclusive: int | None = None
    confidence: float = 1.0
    bindings: tuple[tuple[str, tuple[int, ...]], ...] = ()


class _ExactPatternIndex:
    """Aho-Corasick index for fixed tile patterns."""

    def __init__(self, lexemes: list[dict[str, Any]]):
        self._edges: list[dict[int, int]] = [{}]
        self._fail = [0]
        self._outputs: list[list[dict[str, Any]]] = [[]]
        for lexeme in lexemes:
            if lexeme["variablePositions"]:
                continue
            node = 0
            for value in lexeme["pattern"]:
                node = self._edges[node].setdefault(value, len(self._edges))
                if node == len(self._edges):
                    self._edges.append({})
                    self._fail.append(0)
                    self._outputs.append([])
            self._outputs[node].append(lexeme)
        queue = deque(self._edges[0].values())
        while queue:
            node = queue.popleft()
            for value, target in self._edges[node].items():
                queue.append(target)
                fallback = self._fail[node]
                while fallback and value not in self._edges[fallback]:
                    fallback = self._fail[fallback]
                self._fail[target] = self._edges[fallback].get(value, 0)
                self._outputs[target].extend(self._outputs[self._fail[target]])

    def search(
        self, row: tuple[int | None, ...]
    ) -> list[tuple[dict[str, Any], int]]:
        result = []
        node = 0
        for column, value in enumerate(row):
            if value is None:
                node = 0
                continue
            while node and value not in self._edges[node]:
                node = self._fail[node]
            node = self._edges[node].get(value, 0)
            for lexeme in self._outputs[node]:
                result.append((lexeme, column - len(lexeme["pattern"]) + 1))
        return result


class NametableTextRunState:
    """Apply sparse writes without ever rescanning or rereading the PPU."""

    def __init__(self, width: int = 32):
        if width <= 0:
            raise ValueError("Nametable width must be positive")
        self.width = width
        self._rows: dict[int, list[int | None]] = {}
        self._glyph_rows: dict[int, list[bool | None]] = {}

    def apply(self, event: dict[str, Any]) -> tuple[int, ...]:
        if event.get("type") != "writes" or not isinstance(event.get("runs"), list):
            raise ValueError("expected a text-run writes event")
        changed_rows = set()
        for item in event["runs"]:
            if not isinstance(item, dict):
                raise ValueError("text run must be an object")
            row = item.get("row")
            start = item.get("startColumn")
            if not isinstance(row, int) or row < 0:
                raise ValueError("text run row must be non-negative")
            if not isinstance(start, int) or start < 0:
                raise ValueError("text run startColumn must be non-negative")
            try:
                values = bytes.fromhex(str(item.get("hex", "")))
            except ValueError as error:
                raise ValueError("text run hex is invalid") from error
            if not values or start + len(values) > self.width:
                raise ValueError("text run exceeds its Nametable row")
            target = self._rows.setdefault(row, [None] * self.width)
            glyph_target = self._glyph_rows.setdefault(row, [None] * self.width)
            glyph_mask = item.get("glyphMask")
            if glyph_mask is not None and (
                not isinstance(glyph_mask, str)
                or len(glyph_mask) != len(values)
                or any(marker not in "01" for marker in glyph_mask)
            ):
                raise ValueError("text run glyphMask is invalid")
            for offset, value in enumerate(values):
                target[start + offset] = value
                glyph_target[start + offset] = (
                    glyph_mask[offset] == "1" if glyph_mask is not None else None
                )
            changed_rows.add(row)
        return tuple(sorted(changed_rows))

    def row(self, row: int) -> tuple[int | None, ...]:
        return tuple(self._rows.get(row, [None] * self.width))

    def glyph_status(self, row: int, column: int) -> bool | None:
        return self._glyph_rows.get(row, [None] * self.width)[column]

    def known_runs(self, row: int) -> tuple[TextRun, ...]:
        result = []
        start: int | None = None
        values: list[int] = []
        for column, value in enumerate(self.row(row)):
            if value is not None:
                if start is None:
                    start = column
                values.append(value)
            elif start is not None:
                result.append(TextRun(row, start, tuple(values)))
                start = None
                values = []
        if start is not None:
            result.append(TextRun(row, start, tuple(values)))
        return tuple(result)

    def text_lines(
        self,
        *,
        excluded_cells: frozenset[tuple[int, int]] = frozenset(),
        glyph_values: frozenset[int] | None = None,
        max_space_gap: int | None = None,
    ) -> tuple[TextLine, ...]:
        """Return conservative lines without guessing across unknown cells.

        DQRUN is already a text-write stream, so every known value is a text
        cell. Stable-provenance cells are removed before grouping; removing a
        cell splits a line instead of allowing fallback to claim through it.
        """
        if glyph_values is not None:
            result = []
            for row in sorted(self._rows):
                values = self.row(row)
                glyph_columns = [
                    column for column, value in enumerate(values)
                    if value in glyph_values
                    and self.glyph_status(row, column) is not False
                    and (row, column) not in excluded_cells
                ]
                if not glyph_columns:
                    continue
                groups: list[list[int]] = [[glyph_columns[0]]]
                for column in glyph_columns[1:]:
                    previous = groups[-1][-1]
                    gap = values[previous + 1:column]
                    within_gap_limit = (
                        max_space_gap is None
                        or column - previous - 1 <= max_space_gap
                    )
                    if within_gap_limit and all(
                        value is None or (
                            value == 0x5F
                            and self.glyph_status(
                                row, previous + 1 + offset
                            ) is not False
                        )
                        for offset, value in enumerate(gap)
                    ):
                        groups[-1].append(column)
                    else:
                        groups.append([column])
                for columns in groups:
                    start, end = columns[0], columns[-1] + 1
                    # An unwritten cell inside a line is visually blank until
                    # proven otherwise. Preserve its column as the canonical
                    # blank tile so templates and bounding boxes keep their
                    # screen geometry.
                    line_values = tuple(
                        0x5F if value is None else int(value)
                        for value in values[start:end]
                    )
                    line_cells = tuple(
                        ScreenCell(row, column, int(values[column]))
                        for column in range(start, end)
                        if values[column] is not None
                    )
                    result.append(TextLine(
                        line_id=(
                            f"row-{row}:{start}-{end}:"
                            f"{bytes(line_values).hex()}"
                        ),
                        row=row,
                        start_column=start,
                        values=line_values,
                        cells=line_cells,
                    ))
            return tuple(result)

        result = []
        for row in sorted(self._rows):
            start: int | None = None
            values: list[int] = []
            cells: list[ScreenCell] = []

            def flush() -> None:
                nonlocal start, values, cells
                if start is not None and values:
                    result.append(TextLine(
                        line_id=(
                            f"row-{row}:{start}-{start + len(values)}:"
                            f"{bytes(values).hex()}"
                        ),
                        row=row,
                        start_column=start,
                        values=tuple(values),
                        cells=tuple(cells),
                    ))
                start = None
                values = []
                cells = []

            for column, value in enumerate(self.row(row)):
                if value is None or (row, column) in excluded_cells:
                    flush()
                    continue
                if start is None:
                    start = column
                values.append(value)
                cells.append(ScreenCell(row, column, value))
            flush()
        return tuple(result)


class NametableTextMatcher:
    """Match declarative vocabulary against incrementally maintained rows."""

    _MODIFIERS = frozenset((0xF8, 0xF9))

    def __init__(
        self, vocabulary: dict[str, Any], catalog: dict[str, Any],
        dialogue_translations: dict[str, Any] | None = None,
        dialogue_catalog: dict[str, Any] | None = None,
        character_map: dict[int, dict[str, Any]] | None = None,
    ):
        vocabulary = normalize_vocabulary(vocabulary)
        self.state = NametableTextRunState()
        self._lexemes = []
        self._actions = {}
        self._visible_lexeme_matches: tuple[VisibleLexemeMatch, ...] = ()
        self._visible_screen_text_matches: tuple[VisibleScreenTextMatch, ...] = ()
        self._text_lines: tuple[TextLine, ...] = ()
        self._line_source_matches: tuple[LineSourceMatch, ...] = ()
        self._block_candidates: tuple[TextBlockCandidate, ...] = ()
        self._observed_text_lines: tuple[TextLine, ...] = ()
        self._visual_regions: tuple[VisualTextRegion, ...] = ()
        self._sourced_cells: frozenset[tuple[int, int]] = frozenset()
        self._character_map = character_map or {}
        self._glyph_values = frozenset(
            value for value, entry in self._character_map.items()
            if entry.get("type") == "glyph"
            and (
                not isinstance(entry.get("display"), str)
                or bool(str(entry["display"]).strip())
            )
        )
        self._background_values = frozenset(
            value for value, entry in self._character_map.items()
            if entry.get("type") == "glyph"
            and isinstance(entry.get("display"), str)
            and not str(entry["display"]).strip()
        ) | frozenset((0x5F,))
        for record in vocabulary.get("records", []):
            for source_hex in record_ppu_patterns(
                record, catalog.get("entries", [])
            ):
                candidate = dict(record)
                pattern, variable_positions = self._pattern(
                    bytes.fromhex(source_hex)
                )
                candidate["pattern"] = pattern
                candidate["variablePositions"] = variable_positions
                candidate["tileAlternatives"] = self._tile_alternatives(
                    candidate, pattern, variable_positions
                )
                if pattern:
                    self._lexemes.append(candidate)
            if isinstance(record.get("composition"), dict):
                self._actions[record["id"]] = record
        self._exact_index = _ExactPatternIndex(self._lexemes)
        self._variable_lexemes = [
            item for item in self._lexemes if item["variablePositions"]
        ]
        self._screen_texts = self._build_screen_texts(
            dialogue_translations or {}, dialogue_catalog or {}, character_map
        )
        # A package may contain exact PPU vocabulary before every visual tile
        # has acquired a semantic character-map label (notably compact
        # katakana tables and numeric/status tiles). Exact package patterns
        # are still authoritative evidence that these values are text. Keep
        # character decoding conservative while allowing grouping and
        # template alignment to span those reviewed glyphs.
        package_glyph_values = {
            value
            for lexeme in self._lexemes
            for value in lexeme.get("pattern", ())
            if value not in self._background_values
        }
        for screen_text in self._screen_texts:
            for row in screen_text.get("templateRows", screen_text.get("rows", ())):
                package_glyph_values.update(
                    value for value in row
                    if isinstance(value, int)
                    and value not in self._background_values
                    and value not in self._MODIFIERS
                )
        self._glyph_values = self._glyph_values | frozenset(package_glyph_values)

    @classmethod
    def _build_screen_texts(
        cls, translations: dict[str, Any], catalog: dict[str, Any],
        character_map: dict[int, dict[str, Any]] | None = None,
    ) -> tuple[dict[str, Any], ...]:
        """Compile translated records or segments into screen row patterns."""
        catalog_by_id = {}
        for item in catalog.get("records", []):
            if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                continue
            catalog_by_id[item["id"]] = item
            for unit in item.get("messageUnits", []):
                if isinstance(unit, dict) and isinstance(unit.get("id"), str):
                    catalog_by_id[unit["id"]] = unit
        result = []
        for record in translations.get("records", []):
            source = catalog_by_id.get(str(record.get("id", "")))
            if source is None:
                source = catalog_by_id.get(
                    record.get("catalogRecordId", record.get("id"))
                )
            text = record.get("translation")
            if source is None or not isinstance(text, str) or not text:
                continue
            try:
                values = bytes.fromhex(str(source.get("expandedHex", "")))
            except ValueError:
                continue
            # FF is a message branch whose final screen shape is not known
            # statically. Runtime substitutions are supported when the
            # translation record declares their slots below.
            if not values or 0xFF in values:
                continue
            runtime_composition = record.get("screenTemplate")
            if not isinstance(runtime_composition, dict):
                runtime_composition = record.get("runtimeComposition")
            runtime_parameters = (
                runtime_composition.get("parameters", {})
                if isinstance(runtime_composition, dict) else {}
            )
            slot_names = [
                str(name) for name in runtime_parameters
                if isinstance(name, str) and name
            ]
            # Derive control-byte-to-slot bindings from package metadata. The
            # matcher never assigns a game-specific meaning to FD/F2/etc.
            control_slots: dict[int, str] = {}
            remaining_slots = iter(slot_names)
            for token in source.get("tokens", []):
                if not isinstance(token, dict) or token.get("kind") != "control":
                    continue
                value = token.get("value")
                if not isinstance(value, int) or value in (0xFC, 0xFE, 0xFF):
                    continue
                entry = character_map.get(value) if character_map else None
                display = entry.get("display") if entry else None
                if (
                    isinstance(display, str)
                    and display.startswith("{") and display.endswith("}")
                ):
                    continue
                if value not in control_slots:
                    name = next(remaining_slots, None)
                    if name is not None:
                        control_slots[value] = name
            # Each token is (logical glyph index, tile value) or
            # (None, "{PLACEHOLDER}"). Keeping placeholders here is what
            # lets the Nametable path recognize runtime-expanded templates.
            indexed_rows: list[list[tuple[int | None, int | str]]] = []
            logical_index = 0
            indexed_current: list[tuple[int | None, int | str]] = []
            if character_map is not None:
                for value in values:
                    entry = character_map.get(value)
                    entry_type = entry.get("type") if entry else None
                    display = entry.get("display") if entry else None
                    if value == 0xFC:
                        break
                    if value == 0xFE:
                        if indexed_current:
                            indexed_rows.append(indexed_current)
                            indexed_current = []
                    elif entry_type == "glyph":
                        indexed_current.append((logical_index, value))
                        logical_index += 1
                    elif entry_type == "modifier":
                        continue
                    elif (
                        isinstance(display, str)
                        and display.startswith("{") and display.endswith("}")
                        and len(display) > 2
                    ):
                        indexed_current.append((None, display))
                    elif value in control_slots:
                        indexed_current.append((None, "{" + control_slots[value] + "}"))
                    # Controls and unresolved runtime substitutions do not
                    # consume a logical glyph index. The surrounding known
                    # glyphs still form a useful package-query line.
                if indexed_current:
                    indexed_rows.append(indexed_current)

            segments = record.get("segments")
            if character_map is not None and isinstance(segments, list):
                for segment_index, segment in enumerate(segments):
                    if not isinstance(segment, dict):
                        continue
                    start = segment.get("sourceStart")
                    end = segment.get("sourceEndExclusive")
                    target_lines = segment.get("lines")
                    if (
                        not isinstance(start, int) or not isinstance(end, int)
                        or end <= start or not isinstance(target_lines, list)
                        or not all(isinstance(line, str) for line in target_lines)
                    ):
                        continue
                    segment_rows = []
                    template_rows = []
                    for row in indexed_rows:
                        selected_positions = [
                            position for position, (index, _) in enumerate(row)
                            if index is not None and start <= index < end
                        ]
                        if not selected_positions:
                            continue
                        first, last = min(selected_positions), max(selected_positions)
                        if not any(
                            index is not None for index, _ in row[:first]
                        ):
                            first = 0
                        if not any(
                            index is not None for index, _ in row[last + 1:]
                        ):
                            last = len(row) - 1
                        selected = row[first:last + 1]
                        fixed = tuple(
                            value for _, value in selected
                            if isinstance(value, int)
                        )
                        if not fixed:
                            continue
                        segment_rows.append(fixed)
                        template_rows.append(tuple(value for _, value in selected))
                    segment_rows = tuple(segment_rows)
                    if segment_rows:
                        result.append({
                            "id": f"{record['id']}#segment-{segment_index}",
                            "recordId": str(record["id"]),
                            "text": "\n".join(target_lines),
                            "rows": segment_rows,
                            "templateRows": tuple(template_rows),
                            "translationTemplate": (
                                runtime_composition.get("template")
                                if isinstance(runtime_composition, dict)
                                else None
                            ),
                            "slotDefinitions": runtime_parameters,
                            "sourceStart": start,
                            "sourceEndExclusive": end,
                        })
                if any(
                    item.get("recordId") == str(record["id"]) for item in result
                ):
                    continue

            rows: list[tuple[int, ...]] = []
            current: list[int] = []
            for value in values:
                if value == 0xFC:
                    break
                if value == 0xFE:
                    if current:
                        rows.append(tuple(current))
                        current = []
                    continue
                if value not in cls._MODIFIERS:
                    current.append(value)
            if current:
                rows.append(tuple(current))
            if rows:
                result.append({
                    "id": str(record["id"]),
                    "recordId": str(record["id"]),
                    "text": text,
                    "rows": tuple(rows),
                    "sourceStart": 0,
                    "sourceEndExclusive": logical_index,
                })
        return tuple(result)

    @staticmethod
    def _line_contains(
        line: TextLine, pattern: tuple[int, ...]
    ) -> tuple[int, ...]:
        """Find exact package lines inside one conservative screen line."""
        if len(pattern) > len(line.values):
            return ()
        return tuple(
            offset
            for offset in range(len(line.values) - len(pattern) + 1)
            if line.values[offset:offset + len(pattern)] == pattern
        )

    @staticmethod
    def _template_line_match(
        line: TextLine, template: tuple[int | str, ...]
    ) -> tuple[int, int, tuple[tuple[str, tuple[int, ...]], ...]] | None:
        """Match fixed source fragments separated by bounded placeholders.

        Spaces are layout, not semantic content, for this template path. The
        fixed fragments must cover both ends of the recognized line; only an
        explicit package placeholder may consume otherwise-unmatched glyphs.
        """
        if not any(isinstance(token, str) for token in template):
            return None
        visible = [
            (offset, value) for offset, value in enumerate(line.values)
            if value != 0x5F
        ]
        tokens = [value for _, value in visible]
        parts: list[tuple[str, str | tuple[int, ...]]] = []
        fixed: list[int] = []
        for token in template:
            if isinstance(token, int):
                if token != 0x5F:
                    fixed.append(token)
                continue
            if fixed:
                parts.append(("fixed", tuple(fixed)))
                fixed = []
            parts.append(("slot", token[1:-1]))
        if fixed:
            parts.append(("fixed", tuple(fixed)))

        cursor = 0
        bindings: list[tuple[str, tuple[int, ...]]] = []
        for index, (kind, value) in enumerate(parts):
            if kind == "fixed":
                pattern = value
                assert isinstance(pattern, tuple)
                if tokens[cursor:cursor + len(pattern)] != list(pattern):
                    return None
                cursor += len(pattern)
                continue
            name = value
            assert isinstance(name, str)
            next_fixed = next((
                part_value for part_kind, part_value in parts[index + 1:]
                if part_kind == "fixed"
            ), None)
            if next_fixed is None:
                end = len(tokens)
            else:
                assert isinstance(next_fixed, tuple)
                end = next((
                    position for position in range(cursor + 1, len(tokens) + 1)
                    if tokens[position:position + len(next_fixed)]
                    == list(next_fixed)
                ), -1)
                if end < 0:
                    return None
            captured = tuple(tokens[cursor:end])
            if not 1 <= len(captured) <= 12:
                return None
            bindings.append((name, captured))
            cursor = end
        if cursor != len(tokens) or not visible:
            return None
        return visible[0][0], visible[-1][0] - visible[0][0] + 1, tuple(bindings)

    def _binding_text(
        self, name: str, values: tuple[int, ...], definition: Any
    ) -> str:
        """Resolve one captured slot through the package vocabulary."""
        allowed_categories = set()
        if isinstance(definition, dict):
            categories = definition.get("categories", [])
            if isinstance(categories, list):
                allowed_categories = {
                    str(category) for category in categories
                    if isinstance(category, str)
                }
        candidates = [
            item for item in self._lexemes
            if tuple(item.get("pattern", ())) == values
            and (
                not allowed_categories
                or str(item.get("category", "")) in allowed_categories
            )
        ]
        displays = {
            str(item.get("display", item.get("translation", "")))
            for item in candidates
            if item.get("display", item.get("translation"))
        }
        if len(displays) == 1:
            return next(iter(displays))
        # A non-vocabulary slot such as PLAYER_NAME remains useful in a
        # translated template. Decode it from the same character map.
        return "".join(
            str(self._character_map.get(value, {}).get("display", ""))
            for value in values
        )

    def _render_screen_text(
        self, spec: dict[str, Any],
        bindings: tuple[tuple[str, tuple[int, ...]], ...],
    ) -> str:
        template = spec.get("translationTemplate")
        if not isinstance(template, str) or not template:
            return str(spec["text"])
        definitions = spec.get("slotDefinitions", {})
        result = template
        for name, values in bindings:
            definition = definitions.get(name) if isinstance(definitions, dict) else None
            result = result.replace(
                "{" + name + "}", self._binding_text(name, values, definition)
            )
        # Do not publish a half-resolved translation template.
        if "{" in result and "}" in result:
            return str(spec["text"])
        return result

    def _build_block_candidates(
        self, lines: tuple[TextLine, ...]
    ) -> tuple[
        tuple[LineSourceMatch, ...], tuple[TextBlockCandidate, ...]
    ]:
        """Query lines first, then join common records in source order."""
        specs = {str(item["id"]): item for item in self._screen_texts}
        matches: list[LineSourceMatch] = []
        occurrences: dict[
            tuple[str, str, int],
            list[tuple[int, int, str, tuple[tuple[str, tuple[int, ...]], ...]]],
        ] = {}
        for line in lines:
            for spec in self._screen_texts:
                patterns = spec["rows"]
                for source_index, pattern in enumerate(patterns):
                    offsets = self._line_contains(line, pattern)
                    found = [
                        (offset, len(pattern), "ExactLine", ())
                        for offset in offsets
                    ]
                    template_rows = spec.get("templateRows", ())
                    if source_index < len(template_rows):
                        template_match = self._template_line_match(
                            line, template_rows[source_index]
                        )
                        if template_match is not None:
                            offset, length, bindings = template_match
                            found.append((offset, length, "TemplateLine", bindings))
                    if not found:
                        continue
                    # Prefer a template match when it explains the runtime
                    # material between the fixed fragments.
                    best = max(
                        found,
                        key=lambda item: (item[2] == "TemplateLine", item[1]),
                    )
                    matches.append(LineSourceMatch(
                        line_id=line.line_id,
                        source_unit_id=str(spec["id"]),
                        record_id=str(spec["recordId"]),
                        source_line_index=source_index,
                        source_line_count=len(patterns),
                        score=len(pattern) * len(pattern),
                        match_type=best[2],
                        bindings=best[3],
                    ))
                    occurrences[(
                        line.line_id, str(spec["id"]), source_index
                    )] = found

        ordered = sorted(lines, key=lambda item: (item.row, item.start_column))
        lines_by_id = {item.line_id: item for item in ordered}
        candidates: list[TextBlockCandidate] = []
        for start in range(len(ordered)):
            first = ordered[start]
            first_matches = [item for item in matches if item.line_id == first.line_id]
            for seed in first_matches:
                chain = [first]
                source_end = seed.source_line_index + 1
                score = seed.score
                match_types = [seed.match_type]
                bindings = list(seed.bindings)
                while len(chain) < 4:
                    previous_line = chain[-1]
                    next_options = [
                        (item, lines_by_id[item.line_id])
                        for item in matches
                        if item.source_unit_id == seed.source_unit_id
                        and item.source_line_index == source_end
                        and 1 <= (
                            lines_by_id[item.line_id].row - previous_line.row
                        ) <= 3
                    ]
                    if not next_options:
                        break
                    # Prefer the regular vertical rhythm, then the closest
                    # indentation. This is only a hypothesis score precursor;
                    # complete-record and ambiguity checks still gate output.
                    next_match, next_line = min(
                        next_options,
                        key=lambda pair: (
                            abs((pair[1].row - previous_line.row) - 2),
                            abs(pair[1].start_column - previous_line.start_column),
                            pair[1].row,
                            pair[1].start_column,
                        ),
                    )
                    chain.append(next_line)
                    source_end += 1
                    score += next_match.score
                    match_types.append(next_match.match_type)
                    bindings.extend(next_match.bindings)

                spec = specs[seed.source_unit_id]
                if source_end - seed.source_line_index != len(chain):
                    continue
                cell_set: set[tuple[int, int]] = set()
                for line, source_index in zip(
                    chain, range(seed.source_line_index, source_end)
                ):
                    pattern = spec["rows"][source_index]
                    occurrence_options = occurrences[
                        (line.line_id, seed.source_unit_id, source_index)
                    ]
                    offset, length, _, _ = max(
                        occurrence_options,
                        key=lambda item: (item[2] == "TemplateLine", item[1]),
                    )
                    cell_set.update(
                        (line.row, line.start_column + offset + index)
                        for index in range(length)
                    )
                candidates.append(TextBlockCandidate(
                    source_unit_id=seed.source_unit_id,
                    record_id=seed.record_id,
                    text=self._render_screen_text(spec, tuple(bindings)),
                    lines=tuple(chain),
                    source_line_start=seed.source_line_index,
                    source_line_end_exclusive=source_end,
                    source_line_count=len(spec["rows"]),
                    source_start=spec.get("sourceStart"),
                    source_end_exclusive=spec.get("sourceEndExclusive"),
                    score=score + len(chain) * 100,
                    cells=frozenset(cell_set),
                    match_type=(
                        "NametableTemplate"
                        if "TemplateLine" in match_types
                        else "NametableBlock"
                    ),
                    bindings=tuple(bindings),
                ))
        return tuple(matches), tuple(candidates)

    def _package_assisted_lines(self) -> tuple[TextLine, ...]:
        """Recover exact lines whose explicit blank cells were never written.

        The shadow grid is sparse: an unwritten cell can already contain the
        game's blank tile. Package patterns may therefore bridge `None` only
        where the expected source token is the explicit 0x5F space. No other
        unknown value is guessed.
        """
        result: dict[tuple[int, int, tuple[int, ...]], TextLine] = {}
        locations: dict[int, list[tuple[int, int]]] = {}
        for row_index in range(30):
            for column, value in enumerate(self.state.row(row_index)):
                if value is not None:
                    locations.setdefault(value, []).append((row_index, column))
        for spec in self._screen_texts:
            for pattern in spec["rows"]:
                # Ordinary patterns are already found inside observed
                # TextLines. This supplemental path exists only for a sparse
                # shadow row where an explicit source space (0x5F) was never
                # written and is represented by None.
                if 0x5F not in pattern:
                    continue
                anchor = next((
                    (offset, value) for offset, value in enumerate(pattern)
                    if value != 0x5F
                ), None)
                if anchor is None:
                    continue
                anchor_offset, anchor_value = anchor
                for row_index, anchor_column in locations.get(anchor_value, []):
                    column = anchor_column - anchor_offset
                    if column < 0 or column + len(pattern) > self.state.width:
                        continue
                    row = self.state.row(row_index)
                    if not all(
                        row[column + offset] == expected
                        or (expected == 0x5F and row[column + offset] is None)
                        for offset, expected in enumerate(pattern)
                    ):
                        continue
                    key = (row_index, column, pattern)
                    result[key] = TextLine(
                        line_id=(
                            f"row-{row_index}:{column}-"
                            f"{column + len(pattern)}:{bytes(pattern).hex()}"
                        ),
                        row=row_index,
                        start_column=column,
                        values=pattern,
                        cells=tuple(
                            ScreenCell(row_index, column + offset, value)
                            for offset, value in enumerate(pattern)
                        ),
                    )
        return tuple(sorted(
            result.values(),
            key=lambda item: (item.row, item.start_column, len(item.values)),
        ))

    def _visible_screen_texts(self) -> list[VisibleScreenTextMatch]:
        # Nametable-first dialogue recognition is deliberately independent of
        # provenance. A partially propagated source must not both fail to
        # produce a source block and suppress the content path. Provenance can
        # contribute confidence later; it is not an exclusion mask here.
        observed_lines = self.state.text_lines(
            glyph_values=self._glyph_values or None
        )
        self._visual_regions = self._build_visual_regions()
        self._observed_text_lines = observed_lines
        line_keys = {
            (item.row, item.start_column, item.values): item
            for item in (*observed_lines, *self._package_assisted_lines())
        }
        self._text_lines = tuple(sorted(
            line_keys.values(),
            key=lambda item: (item.row, item.start_column, len(item.values)),
        ))
        line_matches, candidates = self._build_block_candidates(self._text_lines)
        self._line_source_matches = line_matches
        self._block_candidates = candidates

        # Publishing is intentionally stricter than candidate generation:
        # the first implementation only emits complete fixed records. Group
        # hypotheses remain available for diagnostics and later projection.
        complete = [
            item for item in candidates
            if item.complete_record or len(item.lines) >= 2
        ]
        by_cells: dict[frozenset[tuple[int, int]], list[TextBlockCandidate]] = {}
        for item in complete:
            by_cells.setdefault(item.cells, []).append(item)
        safe = []
        for same_cells in by_cells.values():
            translations = {item.text for item in same_cells}
            if len(translations) == 1:
                safe.append(max(same_cells, key=lambda item: item.score))

        selected: list[TextBlockCandidate] = []
        occupied: set[tuple[int, int]] = set()
        for item in sorted(
            safe, key=lambda value: (-value.score, -len(value.cells), value.record_id)
        ):
            if occupied.isdisjoint(item.cells):
                selected.append(item)
                occupied.update(item.cells)
        return sorted((
            VisibleScreenTextMatch(
                source_unit_id=item.source_unit_id,
                record_id=item.record_id,
                text=item.text,
                left=min(column for _, column in item.cells),
                top=min(row for row, _ in item.cells),
                right=max(column for _, column in item.cells) + 1,
                bottom=max(row for row, _ in item.cells) + 1,
                cells=item.cells,
                line_count=len(item.lines),
                source_line_start=item.source_line_start,
                source_line_end_exclusive=item.source_line_end_exclusive,
                source_start=item.source_start,
                source_end_exclusive=item.source_end_exclusive,
                confidence=1.0 if item.complete_record else 0.9,
                match_type=item.match_type,
                bindings=item.bindings,
            )
            for item in selected
        ), key=lambda item: (item.top, item.left))

    def _build_visual_regions(self) -> tuple[VisualTextRegion, ...]:
        """Join neighbouring character nodes across compatible backgrounds.

        This deliberately does *not* flood-fill the background. For each
        character it considers only the nearest character to its right and
        below. An edge is added when every intervening tile is an explicitly
        compatible background tile. Consequently a white rule, window art,
        map tile, or any other non-background tile is a barrier without first
        being classified as a game-specific ``border`` tile.
        """
        character_cells = {
            (row, column)
            for row in range(30)
            for column, value in enumerate(self.state.row(row))
            if value in self._glyph_values
            and self.state.glyph_status(row, column) is not False
        }
        if not character_cells:
            return ()

        parent = {cell: cell for cell in character_cells}
        rank = {cell: 0 for cell in character_cells}
        connecting_cells: dict[tuple[int, int], set[tuple[int, int]]] = {
            cell: {cell} for cell in character_cells
        }

        def find(cell: tuple[int, int]) -> tuple[int, int]:
            root = cell
            while parent[root] != root:
                root = parent[root]
            while parent[cell] != cell:
                following = parent[cell]
                parent[cell] = root
                cell = following
            return root

        def union(
            first: tuple[int, int], second: tuple[int, int],
            path: set[tuple[int, int]],
        ) -> None:
            first_root, second_root = find(first), find(second)
            if first_root == second_root:
                connecting_cells[first_root].update(path)
                return
            if rank[first_root] < rank[second_root]:
                first_root, second_root = second_root, first_root
            parent[second_root] = first_root
            connecting_cells[first_root].update(connecting_cells[second_root])
            connecting_cells[first_root].update(path)
            del connecting_cells[second_root]
            if rank[first_root] == rank[second_root]:
                rank[first_root] += 1

        by_row: dict[int, list[int]] = {}
        by_column: dict[int, list[int]] = {}
        for row, column in character_cells:
            by_row.setdefault(row, []).append(column)
            by_column.setdefault(column, []).append(row)

        # Only consecutive character nodes in each direction need checking;
        # a farther node cannot be the nearest neighbour past an intervening
        # character.
        for row, columns in by_row.items():
            ordered_columns = sorted(columns)
            values = self.state.row(row)
            for left, right in zip(ordered_columns, ordered_columns[1:]):
                between = range(left + 1, right)
                if all(
                    values[column] in self._background_values
                    and self.state.glyph_status(row, column) is not False
                    for column in between
                ):
                    union(
                        (row, left), (row, right),
                        {(row, column) for column in between},
                    )
        for column, rows in by_column.items():
            ordered_rows = sorted(rows)
            for top, bottom in zip(ordered_rows, ordered_rows[1:]):
                between = range(top + 1, bottom)
                if all(
                    self.state.row(row)[column] in self._background_values
                    and self.state.glyph_status(row, column) is not False
                    for row in between
                ):
                    union(
                        (top, column), (bottom, column),
                        {(row, column) for row in between},
                    )

        grouped_characters: dict[tuple[int, int], set[tuple[int, int]]] = {}
        for cell in character_cells:
            grouped_characters.setdefault(find(cell), set()).add(cell)
        components = [
            (connecting_cells[root], characters)
            for root, characters in grouped_characters.items()
        ]

        ordered = sorted(
            components,
            key=lambda item: (
                min(row for row, _ in item[0]),
                min(column for _, column in item[0]),
            ),
        )
        result = []
        for index, (cells, characters) in enumerate(ordered, 1):
            # Draw the character envelope plus one tile of context. The cells
            # retained in the component are only the characters and the
            # explicitly verified paths between them, never an open-ended
            # background flood.
            character_top = min(row for row, _ in characters)
            character_left = min(column for _, column in characters)
            character_bottom = max(row for row, _ in characters) + 1
            character_right = max(column for _, column in characters) + 1
            top = max(character_top - 1, 0)
            left = max(character_left - 1, 0)
            bottom = min(character_bottom + 1, 30)
            right = min(character_right + 1, self.state.width)
            clipped = frozenset(
                (row, column) for row, column in cells
                if top <= row < bottom and left <= column < right
            )
            result.append(VisualTextRegion(
                region_id=f"visual-region-{index}",
                top=top, left=left, bottom=bottom, right=right,
                cells=clipped,
                character_cells=frozenset(characters),
            ))
        return tuple(result)

    @classmethod
    def _pattern(cls, values: bytes) -> tuple[tuple[int, ...], frozenset[int]]:
        pattern = []
        variable_positions = set()
        for value in values:
            if value in cls._MODIFIERS:
                if pattern:
                    variable_positions.add(len(pattern) - 1)
            else:
                pattern.append(value)
        return tuple(pattern), frozenset(variable_positions)

    @staticmethod
    def _tile_alternatives(
        candidate: dict[str, Any], pattern: tuple[int, ...],
        variable_positions: frozenset[int],
    ) -> dict[int, frozenset[int]]:
        """Resolve pack-reviewed alternatives for glyphs followed by modifiers.

        A modifier means that the visible tile may differ from the source byte;
        it must not turn that position into an unrestricted wildcard.
        """
        configured = candidate.get("tileAlternatives", {})
        result = {}
        for position in variable_positions:
            values = configured.get(str(position), configured.get(position, []))
            result[position] = frozenset((pattern[position], *map(int, values)))
        return result

    @staticmethod
    def _locations(
        row: tuple[int | None, ...], pattern: tuple[int, ...],
        tile_alternatives: dict[int, frozenset[int]] | None = None,
    ) -> tuple[int, ...]:
        tile_alternatives = tile_alternatives or {}
        return tuple(
            column for column in range(len(row) - len(pattern) + 1)
            if all(
                row[column + offset] is not None
                and (
                    row[column + offset] in tile_alternatives[offset]
                    if offset in tile_alternatives
                    else row[column + offset] == expected
                )
                for offset, expected in enumerate(pattern)
            )
        )

    def _visible_lexemes(self, rows: range) -> list[tuple[dict[str, Any], int, int]]:
        visible = []
        for row_index in rows:
            row = tuple(
                value if self.state.glyph_status(row_index, column) is not False
                else None
                for column, value in enumerate(self.state.row(row_index))
            )
            visible.extend(
                (lexeme, row_index, column)
                for lexeme, column in self._exact_index.search(row)
            )
            for lexeme in self._variable_lexemes:
                for column in self._locations(
                    row, lexeme["pattern"], lexeme["tileAlternatives"]
                ):
                    visible.append((lexeme, row_index, column))
        return [
            item for item in visible
            if all(
                (item[1], item[2] + offset) not in self._sourced_cells
                for offset in range(len(item[0]["pattern"]))
            )
        ]

    @staticmethod
    def _candidate_score(item: tuple[dict[str, Any], int, int]) -> int:
        lexeme, _, _ = item
        length = len(lexeme["pattern"])
        # Squaring length makes one complete phrase beat a partition into
        # shorter contained words with the same total coverage.
        exact_count = length - len(lexeme["variablePositions"])
        return length * length * 100 + exact_count

    @classmethod
    def _best_non_overlapping(
        cls, candidates: list[tuple[dict[str, Any], int, int]]
    ) -> list[tuple[dict[str, Any], int, int]]:
        """Choose maximum-score non-overlapping matches independently per row."""
        selected = []
        rows: dict[int, list[tuple[dict[str, Any], int, int]]] = {}
        for item in candidates:
            rows.setdefault(item[1], []).append(item)
        for row_candidates in rows.values():
            by_interval: dict[tuple[int, int], list[tuple[dict[str, Any], int, int]]] = {}
            for item in row_candidates:
                start = item[2]
                by_interval.setdefault(
                    (start, start + len(item[0]["pattern"])), []
                ).append(item)
            unambiguous = []
            for same_interval in by_interval.values():
                same_interval.sort(key=lambda item: str(item[0]["id"]))
                best_score = max(map(cls._candidate_score, same_interval))
                best = [
                    item for item in same_interval
                    if cls._candidate_score(item) == best_score
                ]
                displays = {str(item[0].get("display", "")) for item in best}
                if len(best) == 1 or len(displays) == 1:
                    unambiguous.append(best[0])
            ordered = sorted(
                unambiguous,
                key=lambda item: (
                    item[2] + len(item[0]["pattern"]), item[2],
                    -len(item[0]["pattern"]), str(item[0]["id"]),
                ),
            )
            ends = [item[2] + len(item[0]["pattern"]) for item in ordered]
            previous = []
            for index, item in enumerate(ordered):
                start = item[2]
                predecessor = index - 1
                while predecessor >= 0 and ends[predecessor] > start:
                    predecessor -= 1
                previous.append(predecessor)
            scores = [0]
            paths: list[list[int]] = [[]]
            for index, item in enumerate(ordered):
                take_from = previous[index] + 1
                take_score = scores[take_from] + cls._candidate_score(item)
                if take_score > scores[-1]:
                    scores.append(take_score)
                    paths.append(paths[take_from] + [index])
                else:
                    scores.append(scores[-1])
                    paths.append(paths[-1])
            selected.extend(ordered[index] for index in paths[-1])
        return sorted(selected, key=lambda item: (item[1], item[2]))

    def _object_rank(
        self, item: tuple[dict[str, Any], int, int], action_row: int,
        action_column: int,
    ) -> tuple[int, int, int, int]:
        lexeme, row_index, column = item
        row = self.state.row(row_index)
        mismatches = sum(
            row[column + offset] != expected
            for offset, expected in enumerate(lexeme["pattern"])
        )
        return (
            mismatches,
            action_row - row_index,
            abs(action_column - column),
            -len(lexeme["pattern"]),
        )

    def apply(self, event: dict[str, Any]) -> VisibleTextMatch | None:
        changed = self.state.apply(event)
        if not changed:
            return None
        return self._refresh_matches()

    def set_sourced_cells(
        self, cells: set[tuple[int, int]] | frozenset[tuple[int, int]]
    ) -> VisibleTextMatch | None:
        """Replace the exact cells owned by stable semantic provenance."""
        incoming = frozenset(cells)
        if incoming == self._sourced_cells:
            return None
        self._sourced_cells = incoming
        return self._refresh_matches()

    def _refresh_matches(self) -> VisibleTextMatch | None:
        # The shadow grid is already in memory; scanning its 30 short rows is
        # cheap and lets an unrelated write preserve the current match while a
        # clearing write naturally removes it.
        visible = self._visible_lexemes(range(30))
        standalone = self._best_non_overlapping([
            item for item in visible if item[0]["id"] not in self._actions
        ])
        screen_texts = self._visible_screen_texts()
        screen_cells = set().union(*(item.cells for item in screen_texts)) \
            if screen_texts else set()
        standalone = [
            item for item in standalone
            if all(
                (item[1], item[2] + offset) not in screen_cells
                for offset in range(len(item[0]["pattern"]))
            )
        ]
        self._visible_lexeme_matches = tuple(
            VisibleLexemeMatch(
                record_id=str(lexeme["id"]), row=row, column=column,
                length=len(lexeme["pattern"]),
            )
            for lexeme, row, column in standalone
        )
        self._visible_screen_text_matches = tuple(screen_texts)
        actions = [item for item in visible if item[0]["id"] in self._actions]
        for action, action_row, action_column in sorted(
            actions, key=lambda item: (item[1], item[2]), reverse=True
        ):
            spec = action["composition"]
            categories = set(spec.get("objectCategories", []))
            objects = [
                item for item in visible
                if item[0].get("category") in categories
                and 0 <= action_row - item[1] <= int(spec.get("maxRowDistance", 3))
            ]
            if categories and not objects:
                continue
            ranked = sorted(
                objects,
                key=lambda item: self._object_rank(
                    item, action_row, action_column
                ),
            )
            selected = ranked[0] if ranked else None
            if selected is not None and len(ranked) > 1:
                best_rank = self._object_rank(selected, action_row, action_column)
                next_rank = self._object_rank(
                    ranked[1], action_row, action_column
                )
                if best_rank == next_rank and selected[0]["id"] != ranked[1][0]["id"]:
                    continue
            amount = ""
            if selected is not None and spec.get("captureAmount"):
                _, object_row, object_column = selected
                row = self.state.row(object_row)
                digits = []
                column = object_column - 1
                while column >= 0 and isinstance(row[column], int) and 0 <= row[column] <= 9:
                    digits.append(str(row[column]))
                    column -= 1
                amount = "".join(reversed(digits))
                if not amount:
                    continue
            text = str(spec["format"])
            text = text.replace(
                "{object}", selected[0]["display"] if selected else ""
            ).replace("{amount}", amount)
            matches = [(action, action_row, action_column)]
            if selected is not None:
                matches.append(selected)
            return VisibleTextMatch(
                action_id=action["id"], text=text,
                left=min(item[2] for item in matches),
                top=min(item[1] for item in matches),
                right=max(item[2] + len(item[0]["pattern"]) for item in matches),
                bottom=max(item[1] for item in matches) + 1,
                object_id=selected[0]["id"] if selected else None,
                object_source_text=(
                    str(selected[0].get("sourceText", "")) if selected else None
                ),
                object_text=(
                    str(selected[0].get("display", "")) if selected else None
                ),
                object_category=(
                    str(selected[0].get("category", "")) if selected else None
                ),
            )
        return None

    @property
    def visible_lexemes(self) -> tuple[VisibleLexemeMatch, ...]:
        """All translated vocabulary terms currently present in the shadow grid."""
        return self._visible_lexeme_matches

    @property
    def visible_screen_texts(self) -> tuple[VisibleScreenTextMatch, ...]:
        return self._visible_screen_text_matches

    @property
    def text_lines(self) -> tuple[TextLine, ...]:
        return self._text_lines

    @property
    def line_source_matches(self) -> tuple[LineSourceMatch, ...]:
        return self._line_source_matches

    @property
    def block_candidates(self) -> tuple[TextBlockCandidate, ...]:
        return self._block_candidates

    @property
    def observed_text_lines(self) -> tuple[TextLine, ...]:
        return self._observed_text_lines

    @property
    def visual_regions(self) -> tuple[VisualTextRegion, ...]:
        return self._visual_regions

    @property
    def recognized_cells(self) -> tuple[ScreenCell, ...]:
        if not self._glyph_values:
            return ()
        return tuple(
            ScreenCell(row, column, int(value))
            for row in range(30)
            for column, value in enumerate(self.state.row(row))
            if value in self._glyph_values
            and self.state.glyph_status(row, column) is not False
        )

    def display_for_value(self, value: int) -> str:
        return str(self._character_map.get(value, {}).get("display", ""))
