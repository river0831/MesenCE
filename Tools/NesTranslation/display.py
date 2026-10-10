"""A deliberately simple renderer for proving the end-to-end data path."""

from __future__ import annotations

from dataclasses import dataclass

from .database import GameDatabase
from .events import TextEvent


@dataclass(frozen=True)
class DisplayCommand:
    type: str
    instance_id: int | None
    text: str | None
    record_id: str | None


class DebugRenderer:
    def __init__(self, database: GameDatabase) -> None:
        self._records = {record.id: record for record in database.records}
        self.current: DisplayCommand | None = None

    def consume(self, event: TextEvent) -> DisplayCommand:
        if event.type == "text-hide":
            command = DisplayCommand("hide", event.instance_id, None, event.record_id)
        else:
            if event.record_id is None or event.record_id not in self._records:
                raise KeyError(f"unknown record id: {event.record_id}")
            record = self._records[event.record_id]
            command = DisplayCommand(
                "show" if event.type == "text-show" else "replace",
                event.instance_id,
                record.translation,
                record.id,
            )
        self.current = command
        return command
