"""Load and validate a translation database against its exact NES ROM."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


INES_HEADER_SIZE = 16


class DatabaseError(ValueError):
    """Raised when a database or its bound ROM is invalid."""


@dataclass(frozen=True)
class ClearRect:
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class OverlayLabel:
    text: str
    x: int
    y: int
    clear: ClearRect
    source_start: int | None = None
    source_end_exclusive: int | None = None


@dataclass(frozen=True)
class Presentation:
    mode: str
    labels: tuple[OverlayLabel, ...]


@dataclass(frozen=True)
class PpuUpdateBuffer:
    ram_start: int
    ram_end_exclusive: int
    entry_size: int
    address_high_offset: int
    address_low_offset: int
    value_offset: int
    writer_pc: int
    confidence: str


@dataclass(frozen=True)
class TextRecord:
    id: str
    kind: str
    prg_start: int
    prg_end_exclusive: int
    raw_bytes: bytes
    source_text: str
    translation: str
    confidence: str
    presentation: Presentation | None
    dismiss_input_mask: int | None
    return_to_record_id: str | None
    deactivation_confidence: str | None

    def contains(self, prg_offset: int) -> bool:
        return self.prg_start <= prg_offset < self.prg_end_exclusive


@dataclass(frozen=True)
class GameDatabase:
    database_version: int
    rom_sha256: str
    prg_file_offset: int
    cpu_address_base: int
    input_address: int
    ppu_update_buffer: PpuUpdateBuffer | None
    records: tuple[TextRecord, ...]

    def records_at(self, prg_offset: int) -> tuple[TextRecord, ...]:
        return tuple(record for record in self.records if record.contains(prg_offset))


def _require(value: dict[str, Any], key: str, expected_type: type) -> Any:
    if key not in value or not isinstance(value[key], expected_type):
        raise DatabaseError(f"{key!r} must be {expected_type.__name__}")
    return value[key]


def _non_negative_int(value: dict[str, Any], key: str, context: str) -> int:
    result = _require(value, key, int)
    if result < 0:
        raise DatabaseError(f"{context}.{key} must be non-negative")
    return result


def _load_presentation(item: dict[str, Any], record_id: str) -> Presentation | None:
    if "presentation" not in item:
        return None
    value = _require(item, "presentation", dict)
    mode = _require(value, "mode", str)
    if mode != "label-overlay":
        raise DatabaseError(f"unsupported presentation mode for {record_id}: {mode}")
    raw_labels = _require(value, "labels", list)
    if not raw_labels:
        raise DatabaseError(f"presentation labels must not be empty for {record_id}")

    labels: list[OverlayLabel] = []
    for index, raw_label in enumerate(raw_labels):
        context = f"presentation.labels[{index}]"
        if not isinstance(raw_label, dict):
            raise DatabaseError(f"{context} must be an object")
        text = _require(raw_label, "text", str)
        if not text:
            raise DatabaseError(f"{context}.text must not be empty")
        clear = _require(raw_label, "clear", dict)
        width = _non_negative_int(clear, "width", f"{context}.clear")
        height = _non_negative_int(clear, "height", f"{context}.clear")
        if width == 0 or height == 0:
            raise DatabaseError(f"{context}.clear dimensions must be positive")
        source_start = raw_label.get("sourceStart")
        source_end = raw_label.get("sourceEndExclusive")
        if (source_start is None) != (source_end is None):
            raise DatabaseError(
                f"{context} source range must provide both endpoints"
            )
        if source_start is not None and (
            not isinstance(source_start, int)
            or not isinstance(source_end, int)
            or source_start < 0
            or source_end <= source_start
        ):
            raise DatabaseError(f"{context} source range is invalid")
        labels.append(OverlayLabel(
            text=text,
            x=_non_negative_int(raw_label, "x", context),
            y=_non_negative_int(raw_label, "y", context),
            clear=ClearRect(
                x=_non_negative_int(clear, "x", f"{context}.clear"),
                y=_non_negative_int(clear, "y", f"{context}.clear"),
                width=width,
                height=height,
            ),
            source_start=source_start,
            source_end_exclusive=source_end,
        ))
    return Presentation(mode=mode, labels=tuple(labels))


def load_database(path: Path) -> GameDatabase:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise DatabaseError("database root must be an object")

    version = _require(raw, "databaseVersion", int)
    if version != 1:
        raise DatabaseError(f"unsupported databaseVersion: {version}")

    rom = _require(raw, "rom", dict)
    sha256 = _require(rom, "sha256", str).lower()
    if len(sha256) != 64 or any(char not in "0123456789abcdef" for char in sha256):
        raise DatabaseError("rom.sha256 must be a lowercase SHA-256 hex digest")
    prg_file_offset = _require(rom, "prgFileOffset", int)
    runtime = _require(raw, "runtime", dict)
    cpu_address_base = _non_negative_int(runtime, "cpuAddressBase", "runtime")
    input_address = _non_negative_int(runtime, "inputAddress", "runtime")
    if cpu_address_base > 0xFFFF or input_address > 0xFFFF:
        raise DatabaseError("runtime addresses must fit in 16 bits")

    ppu_update_buffer: PpuUpdateBuffer | None = None
    if "ppuUpdateBuffer" in runtime:
        buffer = _require(runtime, "ppuUpdateBuffer", dict)
        ram_start = _non_negative_int(buffer, "ramStart", "runtime.ppuUpdateBuffer")
        ram_end = _non_negative_int(
            buffer, "ramEndExclusive", "runtime.ppuUpdateBuffer"
        )
        entry_size = _non_negative_int(
            buffer, "entrySize", "runtime.ppuUpdateBuffer"
        )
        offsets = {
            "addressHighOffset": _non_negative_int(
                buffer, "addressHighOffset", "runtime.ppuUpdateBuffer"
            ),
            "addressLowOffset": _non_negative_int(
                buffer, "addressLowOffset", "runtime.ppuUpdateBuffer"
            ),
            "valueOffset": _non_negative_int(
                buffer, "valueOffset", "runtime.ppuUpdateBuffer"
            ),
        }
        if ram_start >= ram_end or ram_end > 0x800:
            raise DatabaseError("runtime.ppuUpdateBuffer must fit NES internal RAM")
        if entry_size == 0 or any(offset >= entry_size for offset in offsets.values()):
            raise DatabaseError("runtime.ppuUpdateBuffer offsets must fit entrySize")
        if len(set(offsets.values())) != len(offsets):
            raise DatabaseError("runtime.ppuUpdateBuffer offsets must be distinct")
        writer_pc = _non_negative_int(
            buffer, "writerPc", "runtime.ppuUpdateBuffer"
        )
        if writer_pc > 0xFFFF:
            raise DatabaseError("runtime.ppuUpdateBuffer.writerPc must fit 16 bits")
        ppu_update_buffer = PpuUpdateBuffer(
            ram_start=ram_start,
            ram_end_exclusive=ram_end,
            entry_size=entry_size,
            address_high_offset=offsets["addressHighOffset"],
            address_low_offset=offsets["addressLowOffset"],
            value_offset=offsets["valueOffset"],
            writer_pc=writer_pc,
            confidence=_require(buffer, "confidence", str),
        )

    record_values = _require(raw, "records", list)
    records: list[TextRecord] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(record_values):
        if not isinstance(item, dict):
            raise DatabaseError(f"records[{index}] must be an object")
        record_id = _require(item, "id", str)
        if record_id in seen_ids:
            raise DatabaseError(f"duplicate record id: {record_id}")
        seen_ids.add(record_id)

        locator = _require(item, "prgRange", dict)
        start = _require(locator, "start", int)
        end = _require(locator, "endExclusive", int)
        if start < 0 or end <= start:
            raise DatabaseError(f"invalid PRG range for {record_id}")

        raw_hex = _require(item, "rawHex", str)
        try:
            record_bytes = bytes.fromhex(raw_hex)
        except ValueError as error:
            raise DatabaseError(f"invalid rawHex for {record_id}: {error}") from error
        if len(record_bytes) != end - start:
            raise DatabaseError(f"rawHex length does not match PRG range for {record_id}")

        dismiss_input_mask: int | None = None
        return_to_record_id: str | None = None
        deactivation_confidence: str | None = None
        if "deactivation" in item:
            deactivation = _require(item, "deactivation", dict)
            dismiss_input_mask = _require(deactivation, "dismissInputMask", int)
            if dismiss_input_mask < 1 or dismiss_input_mask > 0xFF:
                raise DatabaseError(
                    f"invalid dismissInputMask for {record_id}: {dismiss_input_mask}"
                )
            if "returnToRecordId" in deactivation:
                return_to_record_id = _require(
                    deactivation, "returnToRecordId", str
                )
            deactivation_confidence = _require(deactivation, "confidence", str)

        presentation = _load_presentation(item, record_id)
        if presentation is not None:
            for label in presentation.labels:
                if (
                    label.source_end_exclusive is not None
                    and label.source_end_exclusive > len(record_bytes)
                ):
                    raise DatabaseError(
                        f"presentation label source range exceeds {record_id}"
                    )
        records.append(TextRecord(
            id=record_id,
            kind=_require(item, "kind", str),
            prg_start=start,
            prg_end_exclusive=end,
            raw_bytes=record_bytes,
            source_text=_require(item, "sourceText", str),
            translation=_require(item, "translation", str),
            confidence=_require(item, "confidence", str),
            presentation=presentation,
            dismiss_input_mask=dismiss_input_mask,
            return_to_record_id=return_to_record_id,
            deactivation_confidence=deactivation_confidence,
        ))

    record_ids = {record.id for record in records}
    for record in records:
        if (
            record.return_to_record_id is not None
            and record.return_to_record_id not in record_ids
        ):
            raise DatabaseError(
                f"unknown returnToRecordId for {record.id}: "
                f"{record.return_to_record_id}"
            )

    return GameDatabase(
        version,
        sha256,
        prg_file_offset,
        cpu_address_base,
        input_address,
        ppu_update_buffer,
        tuple(records),
    )


def validate_rom(database: GameDatabase, rom_path: Path) -> None:
    rom = rom_path.read_bytes()
    digest = hashlib.sha256(rom).hexdigest()
    if digest != database.rom_sha256:
        raise DatabaseError(
            f"ROM SHA-256 mismatch: expected {database.rom_sha256}, got {digest}"
        )
    if rom[:4] != b"NES\x1a":
        raise DatabaseError("bound file is not an iNES ROM")

    for record in database.records:
        file_start = database.prg_file_offset + record.prg_start
        actual = rom[file_start:file_start + len(record.raw_bytes)]
        if actual != record.raw_bytes:
            raise DatabaseError(
                f"ROM bytes do not match database record {record.id} at "
                f"PRG 0x{record.prg_start:04X}"
            )
