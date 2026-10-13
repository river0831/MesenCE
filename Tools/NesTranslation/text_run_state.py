"""Incremental shadow state for Nametable text-row write events."""

from __future__ import annotations

from dataclasses import dataclass
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

    def __init__(self, vocabulary: dict[str, Any], catalog: dict[str, Any]):
        entries = {entry["id"]: entry for entry in catalog.get("entries", [])}
        self.state = NametableTextRunState()
        self._lexemes = []
        self._actions = {}
        for record in vocabulary.get("records", []):
            entry = entries.get(record.get("id"))
            if entry is None:
                continue
            candidate = dict(record)
            candidate["pattern"] = self._normalize(bytes.fromhex(entry["rawHex"]))
            self._lexemes.append(candidate)
            if isinstance(candidate.get("composition"), dict):
                self._actions[candidate["id"]] = candidate
        for record in vocabulary.get("ppuLexemes", []):
            candidate = dict(record)
            candidate["pattern"] = self._normalize(
                bytes.fromhex(candidate["sourceHex"])
            )
            self._lexemes.append(candidate)

    @classmethod
    def _normalize(cls, values: bytes) -> tuple[int, ...]:
        return tuple(value for value in values if value not in cls._MODIFIERS)

    @staticmethod
    def _locations(
        row: tuple[int | None, ...], pattern: tuple[int, ...]
    ) -> tuple[int, ...]:
        return tuple(
            column for column in range(len(row) - len(pattern) + 1)
            if row[column:column + len(pattern)] == pattern
        )

    def _visible_lexemes(self, rows: range) -> list[tuple[dict[str, Any], int, int]]:
        visible = []
        for row_index in rows:
            row = self.state.row(row_index)
            for lexeme in self._lexemes:
                for column in self._locations(row, lexeme["pattern"]):
                    visible.append((lexeme, row_index, column))
        return visible

    def apply(self, event: dict[str, Any]) -> VisibleTextMatch | None:
        changed = self.state.apply(event)
        if not changed:
            return None
        # The shadow grid is already in memory; scanning its 30 short rows is
        # cheap and lets an unrelated write preserve the current match while a
        # clearing write naturally removes it.
        visible = self._visible_lexemes(range(30))
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
            selected = min(
                objects,
                key=lambda item: (
                    action_row - item[1], abs(action_column - item[2])
                ),
                default=None,
            )
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
            )
        return None
