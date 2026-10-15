"""Promote safe, reviewed ROM text inventory entries into runtime subtitles."""

from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from .database import DatabaseError


_DYNAMIC_MARKER = re.compile(r"\{[^}]+\}|<[0-9A-Fa-f]{2}>")
_FIXED_TEXT_REASONS = frozenset((
    "short fixed text with only understood layout controls",
    "fixed text, but long or split across several dialogue pages",
    # These records contain game-specific dictionary/control bytes that the
    # generic extractor cannot name, but their complete ROM byte sequence is
    # still stable and therefore safe to bind with static-exact matching.
    "contains unresolved source bytes or non-layout controls",
))


def _is_fixed_candidate(candidate: dict[str, Any]) -> bool:
    return candidate.get("displayDifficultyReason") in _FIXED_TEXT_REASONS


def _wrap_translation(text: str, width: int = 18) -> list[str]:
    """Wrap compact Chinese copy without changing its content."""
    lines: list[str] = []
    for paragraph in text.splitlines() or [text]:
        paragraph = paragraph.strip()
        while len(paragraph) > width:
            split = max(
                (paragraph.rfind(mark, 0, width + 1) + 1
                 for mark in "。！？；，、"),
                default=0,
            )
            if split <= 0:
                split = width
            lines.append(paragraph[:split])
            paragraph = paragraph[split:]
        if paragraph:
            lines.append(paragraph)
    return lines or [text]


def integrate_static_texts(
    dialogue: dict[str, Any],
    catalog: dict[str, Any],
    inventory: dict[str, Any],
    character_map: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    """Add translated, fixed messages absent from the reviewed dialogue set.

    Exact raw-byte agreement binds the human-facing inventory row to the
    runtime catalog record. Complex containers and runtime-substituted
    templates stay out of this generic tier. Extraction difficulty alone does
    not exclude stable bytes: a game-specific control byte can be opaque to the
    generic extractor while remaining an exact and reliable runtime key.
    """
    result = deepcopy(dialogue)
    records = result.setdefault("records", [])
    if not isinstance(records, list):
        raise DatabaseError("dialogue records must be an array")
    existing = {
        record.get("id") for record in records if isinstance(record, dict)
    }
    runtime_by_id = {
        record.get("id"): record
        for record in catalog.get("records", [])
        if isinstance(record, dict)
    }
    promoted: list[str] = []

    def promote(
        *, record_id: str, catalog_record_id: str, source_text: str,
        translation: str, translation_status: Any, runtime: dict[str, Any],
        integration_mode: str, match_raw_hex: str | None = None,
    ) -> None:
        glyph_count = sum(
            1 for token in runtime.get("tokens", [])
            for value in token.get("expanded", [])
            if character_map.get(value, {}).get("type") == "glyph"
        )
        if glyph_count <= 0:
            raise DatabaseError(f"static text has no logical glyph count: {record_id}")
        item = {
            "id": record_id,
            "catalogRecordId": catalog_record_id,
            "sourceText": source_text,
            "translation": translation,
            "integrationMode": integration_mode,
            "translationStatus": translation_status,
            "box": {
                "x": 52, "y": 150, "width": 152, "height": 66,
                "lineHeight": 15,
            },
            "segments": [{
                "id": f"{record_id}#static",
                "sourceStart": 0,
                "sourceEndExclusive": glyph_count,
                "lines": _wrap_translation(translation),
                "confidence": integration_mode,
            }],
        }
        if match_raw_hex is not None:
            item["matchRawHex"] = match_raw_hex
        records.append(item)
        existing.add(record_id)
        promoted.append(record_id)
    for candidate in inventory.get("records", []):
        if not isinstance(candidate, dict):
            continue
        record_id = candidate.get("id")
        translation = candidate.get("translation")
        if not isinstance(record_id, str) or candidate.get("kind") != "chr-record":
            continue
        runtime = runtime_by_id.get(record_id)
        if runtime is None:
            raise DatabaseError(f"static text is absent from runtime catalog: {record_id}")
        if runtime.get("rawHex") != candidate.get("rawHex"):
            raise DatabaseError(f"static text bytes disagree with runtime catalog: {record_id}")
        if (
            record_id not in existing
            and _is_fixed_candidate(candidate)
            and candidate.get("messageUnitCount") == 1
            and isinstance(translation, str) and translation.strip()
            and not _DYNAMIC_MARKER.search(translation)
        ):
            promote(
                record_id=record_id, catalog_record_id=record_id,
                source_text=str(candidate.get("sourceText", "")),
                translation=translation,
                translation_status=candidate.get("translationStatus"),
                runtime=runtime, integration_mode="static-exact",
            )
        if candidate.get("messageUnitCount", 1) <= 1:
            continue
        runtime_units = {
            unit.get("id"): unit for unit in runtime.get("messageUnits", [])
            if isinstance(unit, dict)
        }
        for unit in candidate.get("messageUnits", []):
            if not isinstance(unit, dict):
                continue
            unit_id = unit.get("id")
            unit_translation = unit.get("translation")
            runtime_unit = runtime_units.get(unit_id)
            if (
                not isinstance(unit_id, str) or unit_id in existing
                or not _is_fixed_candidate(unit)
                or not isinstance(unit_translation, str) or not unit_translation.strip()
                or _DYNAMIC_MARKER.search(unit_translation)
                or runtime_unit is None
            ):
                continue
            promote(
                record_id=unit_id, catalog_record_id=record_id,
                source_text=str(unit.get("sourceText", "")),
                translation=unit_translation,
                translation_status=unit.get("translationStatus"),
                runtime=runtime_unit, integration_mode="static-exact-unit",
                match_raw_hex=str(
                    runtime.get("rawHex", "")
                    if runtime_unit.get("ordinal") == 1
                    else runtime_unit.get("rawHex", "")
                ),
            )
    result["staticIntegration"] = {
        "policy": "exact-fixed-message-units",
        "recordCount": len(promoted),
        "recordIds": promoted,
    }
    return result
