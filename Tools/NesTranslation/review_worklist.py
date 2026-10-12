"""Build a lossless, prioritized review worklist from a dialogue catalog."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any


DIALOGUE_MARKERS = ("＊「", "「")
SYSTEM_TERMS = (
    "てにいれた", "みつけた", "もてません", "おかね", "どれを", "なにを",
)
VOCABULARY_TERMS = (
    "かぎ", "たいまつ", "やくそう", "せいすい", "つばさ", "つるぎ",
    "おの", "よろい", "たて", "ゆびわ", "しずく", "ふえ", "つえ",
)


def _suggest_category(record: dict[str, Any], translated_ids: set[str]) -> tuple[str, list[str]]:
    record_id = str(record.get("id", ""))
    decoded = str(record.get("decoded", ""))
    reasons: list[str] = []
    if record_id in translated_ids:
        return "translated-dialogue", ["translation database contains this record ID"]
    if any(term in decoded for term in SYSTEM_TERMS):
        reasons.append("contains a known system-message phrase")
        return "system-or-template", reasons
    if any(marker in decoded for marker in DIALOGUE_MARKERS):
        reasons.append("contains a dialogue speaker marker")
        return "dialogue", reasons
    if any(term in decoded for term in VOCABULARY_TERMS):
        reasons.append("contains a known item or equipment term")
        return "vocabulary-containing", reasons
    return "unclassified", ["no category heuristic matched"]


def _priority(record: dict[str, Any], translated_ids: set[str]) -> tuple[int, str]:
    record_id = str(record.get("id", ""))
    if record_id in translated_ids:
        return 0, "already translated"
    if record.get("runtime", {}).get("status") == "runtime-confirmed":
        return 1, "runtime-confirmed and untranslated"
    likelihood = record.get("evidence", {}).get("likelihood")
    if likelihood == "high":
        return 2, "high static likelihood"
    if likelihood == "medium":
        return 3, "medium static likelihood"
    return 4, "low static likelihood"


def build_worklist(catalog: dict[str, Any], translations: dict[str, Any]) -> dict[str, Any]:
    translated_ids = {
        str(record["id"])
        for record in translations.get("records", [])
        if isinstance(record, dict) and isinstance(record.get("id"), str)
    }
    records = []
    for source in catalog.get("records", []):
        priority, priority_reason = _priority(source, translated_ids)
        category, category_reasons = _suggest_category(source, translated_ids)
        records.append({
            "id": source.get("id"),
            "priority": priority,
            "priorityReason": priority_reason,
            "reviewStatus": (
                "translated" if source.get("id") in translated_ids else "pending"
            ),
            "suggestedCategory": category,
            "categoryEvidence": category_reasons,
            "runtimeStatus": source.get("runtime", {}).get("status", "unverified"),
            "staticLikelihood": source.get("evidence", {}).get("likelihood", "unknown"),
            "score": source.get("metrics", {}).get("score"),
            "glyphCount": source.get("metrics", {}).get("glyphCount"),
            "unknownBytes": source.get("unknownBytes", []),
            "source": source.get("source"),
            "decoded": source.get("decoded", ""),
            "review": {
                "decision": None,
                "category": None,
                "translation": None,
                "notes": None,
            },
        })
    records.sort(key=lambda item: (
        item["priority"],
        -(item["score"] if isinstance(item["score"], (int, float)) else 0),
        item["id"],
    ))
    return {
        "formatVersion": 1,
        "romSha256": catalog.get("romSha256"),
        "policy": {
            "classification": "review suggestion only",
            "preservesAllCatalogRecords": True,
            "promotionRequiresReview": True,
        },
        "summary": {
            "recordCount": len(records),
            "translated": sum(item["reviewStatus"] == "translated" for item in records),
            "pending": sum(item["reviewStatus"] == "pending" for item in records),
            "runtimeConfirmedPending": sum(
                item["runtimeStatus"] == "runtime-confirmed"
                and item["reviewStatus"] == "pending"
                for item in records
            ),
            "bySuggestedCategory": dict(sorted(Counter(
                item["suggestedCategory"] for item in records
            ).items())),
        },
        "records": records,
    }


def render_markdown(worklist: dict[str, Any]) -> str:
    summary = worklist["summary"]
    lines = [
        "# Dragon Quest text review worklist",
        "",
        f"- ROM SHA-256: `{worklist['romSha256']}`",
        f"- Catalog records preserved: {summary['recordCount']}",
        f"- Already translated: {summary['translated']}",
        f"- Pending review: {summary['pending']}",
        f"- Runtime-confirmed and pending: {summary['runtimeConfirmedPending']}",
        "- Categories below are heuristic suggestions, not confirmed semantics.",
        "- Unknown bytes and low-likelihood records remain in the JSON worklist.",
        "",
        "## Suggested-category counts",
        "",
    ]
    for category, count in summary["bySuggestedCategory"].items():
        lines.append(f"- `{category}`: {count}")
    current_priority = None
    for record in worklist["records"]:
        if record["priority"] == 4:
            continue
        if record["priority"] != current_priority:
            current_priority = record["priority"]
            lines.extend(["", f"## Priority {current_priority}: {record['priorityReason']}", ""])
        source = record.get("source") or {}
        unknown = record["unknownBytes"]
        lines.extend([
            f"### {record['id']}",
            "",
            f"- Suggested category: `{record['suggestedCategory']}`",
            f"- Runtime: `{record['runtimeStatus']}`; static: `{record['staticLikelihood']}`; score: `{record['score']}`",
            f"- CHR range: `${source.get('chrStart', 0):04X}-${source.get('chrEndExclusive', 0):04X}`",
            "- Unknown bytes: " + (
                ", ".join(f"`${value:02X}`" for value in unknown) if unknown else "None"
            ),
            "",
            "```text",
            record["decoded"],
            "```",
            "",
        ])
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--translations", required=True, type=Path)
    parser.add_argument("--json-output", required=True, type=Path)
    parser.add_argument("--markdown-output", required=True, type=Path)
    args = parser.parse_args()
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    translations = json.loads(args.translations.read_text(encoding="utf-8"))
    worklist = build_worklist(catalog, translations)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(worklist, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.markdown_output.write_text(render_markdown(worklist), encoding="utf-8")
    summary = worklist["summary"]
    print(
        f"Prepared {summary['recordCount']} records: {summary['translated']} translated, "
        f"{summary['pending']} pending, "
        f"{summary['runtimeConfirmedPending']} runtime-confirmed pending"
    )


if __name__ == "__main__":
    main()
