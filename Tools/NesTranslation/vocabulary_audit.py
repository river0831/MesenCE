"""Audit unified vocabulary coverage and screen-pattern integrity."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable

from .vocabulary import normalize_vocabulary, record_ppu_patterns


def audit_vocabulary(
    vocabulary: dict[str, Any],
    dictionary_catalog: dict[str, Any] | None = None,
    observed_record_ids: Iterable[str] = (),
) -> dict[str, Any]:
    vocabulary = normalize_vocabulary(vocabulary)
    entries = (dictionary_catalog or {}).get("entries", [])
    observed = set(observed_record_ids)
    missing_encodings: list[str] = []
    unresolved_patterns: list[str] = []
    by_pattern: dict[str, list[dict[str, str]]] = defaultdict(list)
    records = vocabulary.get("records", [])

    for record in records:
        record_id = str(record["id"])
        encodings = record.get("encodings", [])
        if not encodings:
            missing_encodings.append(record_id)
            continue
        patterns = record_ppu_patterns(record, entries)
        if not patterns:
            unresolved_patterns.append(record_id)
        for source_hex in patterns:
            canonical = bytes.fromhex(source_hex).hex(" ")
            by_pattern[canonical].append({
                "recordId": record_id,
                "sourceText": str(record.get("sourceText", "")),
                "display": str(record.get("display", record.get("translation", ""))),
            })

    pattern_collisions = []
    pattern_conflicts = []
    for pattern, matches in sorted(by_pattern.items()):
        if len(matches) < 2:
            continue
        item = {"sourceHex": pattern, "records": matches}
        pattern_collisions.append(item)
        if len({match["display"] for match in matches}) > 1:
            pattern_conflicts.append(item)

    configured_ids = {str(record["id"]) for record in records}
    return {
        "summary": {
            "recordCount": len(records),
            "observedRecordCount": len(configured_ids & observed),
            "unobservedRecordCount": len(configured_ids - observed),
            "missingEncodingCount": len(missing_encodings),
            "unresolvedPatternCount": len(unresolved_patterns),
            "patternCollisionCount": len(pattern_collisions),
            "patternConflictCount": len(pattern_conflicts),
        },
        "unobservedRecordIds": sorted(configured_ids - observed),
        "missingEncodingRecordIds": sorted(missing_encodings),
        "unresolvedPatternRecordIds": sorted(unresolved_patterns),
        "patternCollisions": pattern_collisions,
        "patternConflicts": pattern_conflicts,
    }
