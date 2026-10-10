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
class TextRecord:
    id: str
    kind: str
    prg_start: int
    prg_end_exclusive: int
    raw_bytes: bytes
    source_text: str
    translation: str
    confidence: str

    def contains(self, prg_offset: int) -> bool:
        return self.prg_start <= prg_offset < self.prg_end_exclusive


@dataclass(frozen=True)
class GameDatabase:
    database_version: int
    rom_sha256: str
    prg_file_offset: int
    records: tuple[TextRecord, ...]

    def records_at(self, prg_offset: int) -> tuple[TextRecord, ...]:
        return tuple(record for record in self.records if record.contains(prg_offset))


def _require(value: dict[str, Any], key: str, expected_type: type) -> Any:
    if key not in value or not isinstance(value[key], expected_type):
        raise DatabaseError(f"{key!r} must be {expected_type.__name__}")
    return value[key]


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

        records.append(TextRecord(
            id=record_id,
            kind=_require(item, "kind", str),
            prg_start=start,
            prg_end_exclusive=end,
            raw_bytes=record_bytes,
            source_text=_require(item, "sourceText", str),
            translation=_require(item, "translation", str),
            confidence=_require(item, "confidence", str),
        ))

    return GameDatabase(version, sha256, prg_file_offset, tuple(records))


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
