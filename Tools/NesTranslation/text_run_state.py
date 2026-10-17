"""Incremental shadow state for Nametable text-row write events."""

from __future__ import annotations

from dataclasses import dataclass
from collections import deque
from typing import Any


@dataclass(frozen=True)
class TextRun:
    row: int
    start_column: int
    values: tuple[int, ...]


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
    record_id: str
    text: str
    left: int
    top: int
    right: int
    bottom: int
    cells: frozenset[tuple[int, int]]


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
            for offset, value in enumerate(values):
                target[start + offset] = value
            changed_rows.add(row)
        return tuple(sorted(changed_rows))

    def row(self, row: int) -> tuple[int | None, ...]:
        return tuple(self._rows.get(row, [None] * self.width))

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


class NametableTextMatcher:
    """Match declarative vocabulary against incrementally maintained rows."""

    _MODIFIERS = frozenset((0xF8, 0xF9))

    def __init__(
        self, vocabulary: dict[str, Any], catalog: dict[str, Any],
        dialogue_translations: dict[str, Any] | None = None,
        dialogue_catalog: dict[str, Any] | None = None,
    ):
        entries = {entry["id"]: entry for entry in catalog.get("entries", [])}
        self.state = NametableTextRunState()
        self._lexemes = []
        self._actions = {}
        self._visible_lexeme_matches: tuple[VisibleLexemeMatch, ...] = ()
        self._visible_screen_text_matches: tuple[VisibleScreenTextMatch, ...] = ()
        self._sourced_cells: frozenset[tuple[int, int]] = frozenset()
        for record in vocabulary.get("records", []):
            entry = entries.get(record.get("id"))
            if entry is None:
                continue
            candidate = dict(record)
            pattern, variable_positions = self._pattern(
                bytes.fromhex(entry["rawHex"])
            )
            candidate["pattern"] = pattern
            candidate["variablePositions"] = variable_positions
            candidate["tileAlternatives"] = self._tile_alternatives(
                candidate, pattern, variable_positions
            )
            if not pattern:
                continue
            self._lexemes.append(candidate)
            if isinstance(candidate.get("composition"), dict):
                self._actions[candidate["id"]] = candidate
        for record in vocabulary.get("ppuLexemes", []):
            candidate = dict(record)
            pattern, variable_positions = self._pattern(
                bytes.fromhex(candidate["sourceHex"])
            )
            candidate["pattern"] = pattern
            candidate["variablePositions"] = variable_positions
            candidate["tileAlternatives"] = self._tile_alternatives(
                candidate, pattern, variable_positions
            )
            if not pattern:
                continue
            self._lexemes.append(candidate)
        self._exact_index = _ExactPatternIndex(self._lexemes)
        self._variable_lexemes = [
            item for item in self._lexemes if item["variablePositions"]
        ]
        self._screen_texts = self._build_screen_texts(
            dialogue_translations or {}, dialogue_catalog or {}
        )

    @classmethod
    def _build_screen_texts(
        cls, translations: dict[str, Any], catalog: dict[str, Any]
    ) -> tuple[dict[str, Any], ...]:
        """Compile fixed translated records into final-screen row patterns."""
        catalog_by_id = {item["id"]: item for item in catalog.get("records", [])}
        result = []
        for record in translations.get("records", []):
            source = catalog_by_id.get(record.get("catalogRecordId", record.get("id")))
            text = record.get("translation")
            if source is None or not isinstance(text, str) or not text:
                continue
            try:
                values = bytes.fromhex(str(source.get("expandedHex", "")))
            except ValueError:
                continue
            # FD and FF are substitutions/message branches, so they are not
            # fixed final-screen text and must remain source-driven.
            if not values or 0xFD in values or 0xFF in values:
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
                result.append({"id": str(record["id"]), "text": text,
                               "rows": tuple(rows)})
        return tuple(result)

    def _visible_screen_texts(self) -> list[VisibleScreenTextMatch]:
        def screen_locations(
            row: tuple[int | None, ...], pattern: tuple[int, ...]
        ) -> tuple[int, ...]:
            # A cleared window cell can remain unwritten. Visually it is the
            # same blank tile as 0x5F, so fixed text containing spaces must
            # accept either representation without relaxing non-space glyphs.
            return tuple(
                column for column in range(len(row) - len(pattern) + 1)
                if all(
                    row[column + offset] == expected
                    or (expected == 0x5F and row[column + offset] is None)
                    for offset, expected in enumerate(pattern)
                )
            )

        candidates = []
        for spec in self._screen_texts:
            patterns = spec["rows"]
            for top in range(30 - (len(patterns) - 1) * 2):
                locations = [screen_locations(self.state.row(top), patterns[0])]
                if not locations[0]:
                    continue
                for offset, pattern in enumerate(patterns[1:], 1):
                    locations.append(screen_locations(
                        self.state.row(top + offset * 2), pattern
                    ))
                if any(not item for item in locations):
                    continue
                # Lines may use different indentation. Pick the occurrence
                # closest to the first line; the final selection below still
                # rejects overlapping competing records by total coverage.
                columns = [locations[0][0]]
                columns.extend(min(item, key=lambda value: abs(value - columns[0]))
                               for item in locations[1:])
                cells = frozenset(
                    (top + row_offset * 2, column + glyph_offset)
                    for row_offset, (column, pattern) in enumerate(
                        zip(columns, patterns)
                    )
                    for glyph_offset in range(len(pattern))
                )
                if not cells.isdisjoint(self._sourced_cells):
                    continue
                candidates.append(VisibleScreenTextMatch(
                    record_id=spec["id"], text=spec["text"],
                    left=min(columns), top=top,
                    right=max(column + len(pattern) for column, pattern in
                              zip(columns, patterns)),
                    bottom=top + (len(patterns) - 1) * 2 + 1,
                    cells=cells,
                ))
        selected: list[VisibleScreenTextMatch] = []
        occupied: set[tuple[int, int]] = set()
        for item in sorted(candidates, key=lambda value: (-len(value.cells), value.record_id)):
            if occupied.isdisjoint(item.cells):
                selected.append(item)
                occupied.update(item.cells)
        return sorted(selected, key=lambda item: (item.top, item.left))

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
            row = self.state.row(row_index)
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
