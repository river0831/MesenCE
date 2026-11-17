"""Normalize vocabulary records independently of their ROM encoding source."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable

from .database import DatabaseError


def _legacy_encodings(record: dict[str, Any]) -> list[dict[str, Any]]:
    """Translate version-1 source fields into the unified encoding model."""
    result: list[dict[str, Any]] = []
    token = record.get("token")
    if isinstance(token, int):
        result.append({"kind": "dictionary-token", "token": token})
    source_hex = record.get("sourceHex")
    if isinstance(source_hex, str) and source_hex.strip():
        result.append({"kind": "ppu-pattern", "sourceHex": source_hex})
    monster_id = record.get("monsterId")
    if isinstance(monster_id, int):
        result.append({
            "kind": "rom-table", "table": "monsters", "index": monster_id,
        })
    return result


def normalize_vocabulary(vocabulary: dict[str, Any] | None) -> dict[str, Any]:
    """Return one canonical ``records`` collection.

    ``ppuLexemes`` remains accepted as a legacy input, but consumers never need
    to know which top-level array originally contained a record.
    """
    source = vocabulary or {}
    records = source.get("records", [])
    legacy_ppu = source.get("ppuLexemes", [])
    if not isinstance(records, list) or not isinstance(legacy_ppu, list):
        raise DatabaseError("vocabulary records and ppuLexemes must be arrays")

    normalized: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, raw in enumerate((*records, *legacy_ppu)):
        if not isinstance(raw, dict):
            raise DatabaseError(f"vocabulary record {index} must be an object")
        record = deepcopy(raw)
        record_id = record.get("id")
        if not isinstance(record_id, str) or not record_id:
            raise DatabaseError(f"vocabulary record {index} has no valid id")
        if record_id in seen_ids:
            raise DatabaseError(f"duplicate vocabulary record id: {record_id}")
        seen_ids.add(record_id)

        encodings = record.get("encodings")
        if encodings is None:
            encodings = _legacy_encodings(record)
        if not isinstance(encodings, list) or not all(
            isinstance(item, dict) and isinstance(item.get("kind"), str)
            for item in encodings
        ):
            raise DatabaseError(
                f"vocabulary record {record_id} has invalid encodings"
            )
        record["encodings"] = deepcopy(encodings)
        normalized.append(record)

    result = {
        key: deepcopy(value) for key, value in source.items()
        if key not in ("records", "ppuLexemes")
    }
    result["records"] = normalized
    return result


def record_ppu_patterns(
    record: dict[str, Any], dictionary_entries: Iterable[dict[str, Any]],
) -> tuple[str, ...]:
    """Resolve every screen-matchable byte pattern declared by a record."""
    dictionary_entries = tuple(dictionary_entries)
    by_token = {
        entry.get("token"): entry for entry in dictionary_entries
        if isinstance(entry, dict) and isinstance(entry.get("token"), int)
    }
    patterns: list[str] = []
    for encoding in record.get("encodings", []):
        kind = encoding.get("kind")
        if kind == "ppu-pattern":
            source_hex = encoding.get("sourceHex")
            if isinstance(source_hex, str) and source_hex.strip():
                patterns.append(source_hex)
        elif kind == "dictionary-token":
            entry = by_token.get(encoding.get("token"))
            if entry is not None and isinstance(entry.get("rawHex"), str):
                patterns.append(entry["rawHex"])
    # Compatibility for early in-memory callers that paired records and
    # dictionary entries solely by ID. Persisted databases should declare an
    # encoding explicitly; keeping this read path makes the migration safe.
    if not patterns and not record.get("encodings"):
        entry = next(
            (
                item for item in dictionary_entries
                if item.get("id") == record.get("id")
            ),
            None,
        )
        if entry is not None and isinstance(entry.get("rawHex"), str):
            patterns.append(entry["rawHex"])
    return tuple(dict.fromkeys(patterns))
