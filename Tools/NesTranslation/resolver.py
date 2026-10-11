"""Resolve low-level ROM reads into deduplicated text lifecycle events."""

from __future__ import annotations

from .database import GameDatabase, TextRecord
from .events import InputEvent, RomReadEvent, TextEvent


class TextResolver:
    def __init__(self, database: GameDatabase) -> None:
        self.database = database
        self.active_record: TextRecord | None = None
        self.active_instance_id: int | None = None
        self._next_instance_id = 1

    def consume(self, event: RomReadEvent | InputEvent) -> list[TextEvent]:
        if isinstance(event, InputEvent):
            if (
                self.active_record is not None
                and self.active_record.dismiss_input_mask is not None
                and event.buttons & self.active_record.dismiss_input_mask
            ):
                return self.hide(event.frame)
            return []

        matches = self.database.records_at(event.prg_offset)
        if not matches:
            return []

        # The PoC database has non-overlapping locators. Reject ambiguity rather
        # than silently selecting a translation.
        if len(matches) != 1:
            raise RuntimeError(
                f"ambiguous records at PRG 0x{event.prg_offset:04X}: "
                + ", ".join(record.id for record in matches)
            )
        record = matches[0]
        if self.active_record == record:
            return []

        instance_id = self._next_instance_id
        self._next_instance_id += 1
        event_type = "text-show" if self.active_record is None else "text-replace"
        self.active_record = record
        self.active_instance_id = instance_id
        return [TextEvent(
            type=event_type,
            frame=event.frame,
            record_id=record.id,
            instance_id=instance_id,
            evidence_prg_offset=event.prg_offset,
        )]

    def hide(self, frame: int) -> list[TextEvent]:
        if self.active_record is None:
            return []
        result = TextEvent(
            type="text-hide",
            frame=frame,
            record_id=self.active_record.id,
            instance_id=self.active_instance_id,
            evidence_prg_offset=None,
        )
        self.active_record = None
        self.active_instance_id = None
        return [result]
