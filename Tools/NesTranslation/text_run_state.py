"""Incremental shadow state for Nametable text-row write events."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TextRun:
    row: int
    start_column: int
    values: tuple[int, ...]


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
