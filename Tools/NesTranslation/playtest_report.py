"""Summarize translation coverage and review candidates from a playtest."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Any, Iterable

from .snapshot_replay import load_snapshots
from .text_review import load_character_map


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _decoded_sequences(
    values: bytes, character_map: dict[int, dict[str, Any]]
) -> tuple[str, ...]:
    sequences: list[str] = []
    current: list[str] = []
    for value in values:
        entry = character_map.get(value)
        entry_type = entry.get("type") if entry else None
        if entry_type == "glyph":
            current.append(str(entry.get("display", "")))
        elif entry_type == "modifier" and current:
            current.append(str(entry.get("combiningDisplay", entry.get("display", ""))))
        else:
            text = "".join(current).strip()
            if len(text.replace(" ", "")) >= 2:
                sequences.append(text)
            current = []
    text = "".join(current).strip()
    if len(text.replace(" ", "")) >= 2:
        sequences.append(text)
    return tuple(sequences)


def load_text_run_events(path: Path) -> list[dict[str, Any]]:
    events = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), 1
    ):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid text-run JSON at line {line_number}") from error
        if not isinstance(event, dict) or event.get("type") != "writes":
            raise ValueError(f"invalid text-run event at line {line_number}")
        events.append(event)
    return events


def load_discovery_events(path: Path) -> list[dict[str, Any]]:
    events = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), 1
    ):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid discovery JSON at line {line_number}") from error
        if not isinstance(event, dict) or event.get("type") != "catalog-record":
            raise ValueError(f"invalid discovery event at line {line_number}")
        events.append(event)
    return events


def build_playtest_report(
    snapshots: Iterable[dict[str, Any]],
    text_run_events: Iterable[dict[str, Any]],
    character_map: dict[int, dict[str, Any]],
    translations: dict[str, Any],
    vocabulary: dict[str, Any],
    dialogue_catalog: dict[str, Any] | None = None,
    discovery_events: Iterable[dict[str, Any]] = (),
) -> dict[str, Any]:
    snapshots = list(snapshots)
    translated_dialogue = {
        str(record["id"]) for record in translations.get("records", [])
    }
    translated_vocabulary = {
        str(record["id"]) for record in vocabulary.get("records", [])
    }
    known_sources = {
        str(record.get("sourceText", "")).strip()
        for record in vocabulary.get("records", [])
        if str(record.get("sourceText", "")).strip()
    }
    catalog_by_id = {
        str(record["id"]): record
        for record in (dialogue_catalog or {}).get("records", [])
    }
    known_sources.update(
        str(catalog_by_id[record_id].get("decoded", "")).strip()
        for record_id in translated_dialogue if record_id in catalog_by_id
    )

    record_frames: dict[str, set[int]] = defaultdict(set)
    unit_appearances: Counter[str] = Counter()
    instances: dict[str, set[str]] = defaultdict(set)
    parameters: dict[str, Counter[str]] = defaultdict(Counter)
    for snapshot in snapshots:
        frame = int(snapshot["frame"])
        for unit_id in snapshot.get("delta", {}).get("appeared", []):
            unit_appearances[str(unit_id)] += 1
        for item in snapshot.get("items", []):
            record_id = item.get("recordId")
            if not isinstance(record_id, str):
                continue
            record_frames[record_id].add(frame)
            instance_id = item.get("instanceId")
            if isinstance(instance_id, str):
                instances[record_id].add(instance_id)
            for slot, binding in item.get("parameters", {}).items():
                if isinstance(binding, dict) and isinstance(binding.get("text"), str):
                    parameters[str(slot)][binding["text"]] += 1

    candidate_counts: Counter[str] = Counter()
    candidate_examples: dict[str, dict[str, int]] = {}
    for event in text_run_events:
        frame = int(event.get("frame", 0))
        for run in event.get("runs", []):
            try:
                values = bytes.fromhex(str(run.get("hex", "")))
            except ValueError:
                continue
            for text in _decoded_sequences(values, character_map):
                candidate_counts[text] += 1
                candidate_examples.setdefault(text, {
                    "frame": frame,
                    "row": int(run.get("row", 0)),
                    "startColumn": int(run.get("startColumn", 0)),
                })

    def is_known(text: str) -> bool:
        compact = text.replace(" ", "")
        return any(
            compact and compact in source.replace(" ", "")
            for source in known_sources
        )

    candidates = [
        {
            "text": text,
            "occurrences": count,
            "classification": "known-source" if is_known(text) else "needs-review",
            "example": candidate_examples[text],
        }
        for text, count in sorted(
            candidate_counts.items(), key=lambda item: (-item[1], item[0])
        )
    ]
    observed_records = sorted(record_frames)
    discovery_counts = Counter(
        str(event["recordId"])
        for event in discovery_events if isinstance(event.get("recordId"), str)
    )
    discoveries = [
        {
            "recordId": record_id,
            "occurrences": count,
            "translated": record_id in translated_dialogue,
            "sourceText": str(catalog_by_id.get(record_id, {}).get("decoded", "")),
        }
        for record_id, count in sorted(
            discovery_counts.items(), key=lambda item: (-item[1], item[0])
        )
    ]
    return {
        "summary": {
            "snapshotCount": len(snapshots),
            "firstFrame": snapshots[0]["frame"] if snapshots else None,
            "lastFrame": snapshots[-1]["frame"] if snapshots else None,
            "observedRecordCount": len(observed_records),
            "observedInstanceCount": sum(len(value) for value in instances.values()),
            "decodedCandidateCount": len(candidates),
            "reviewCandidateCount": sum(
                item["classification"] == "needs-review" for item in candidates
            ),
            "configuredDialogueCount": len(translated_dialogue),
            "configuredVocabularyCount": len(translated_vocabulary),
            "discoveredCatalogRecordCount": len(discoveries),
            "discoveredUntranslatedCount": sum(
                not item["translated"] for item in discoveries
            ),
        },
        "observedRecords": [
            {
                "recordId": record_id,
                "snapshotFrames": len(record_frames[record_id]),
                "instanceCount": len(instances[record_id]),
                "appearanceCount": sum(
                    count for unit_id, count in unit_appearances.items()
                    if unit_id == record_id or unit_id.startswith(record_id + "#")
                ),
            }
            for record_id in observed_records
        ],
        "parameters": {
            slot: dict(sorted(counts.items()))
            for slot, counts in sorted(parameters.items())
        },
        "catalogDiscoveries": discoveries,
        "textCandidates": candidates,
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Translation playtest report",
        "",
        f"- Frames: {summary['firstFrame']}–{summary['lastFrame']}",
        f"- Snapshots: {summary['snapshotCount']}",
        f"- Observed translated records: {summary['observedRecordCount']}",
        f"- Runtime message instances: {summary['observedInstanceCount']}",
        f"- Decoded text candidates: {summary['decodedCandidateCount']}",
        f"- Candidates needing review: {summary['reviewCandidateCount']}",
        f"- Catalog records discovered: {summary['discoveredCatalogRecordCount']}",
        f"- Discovered without translation: {summary['discoveredUntranslatedCount']}",
        "",
        "## Observed records",
        "",
        "| Record | Snapshot frames | Instances | Appearances |",
        "|---|---:|---:|---:|",
    ]
    for record in report["observedRecords"]:
        lines.append(
            f"| `{record['recordId']}` | {record['snapshotFrames']} | "
            f"{record['instanceCount']} | {record['appearanceCount']} |"
        )
    lines.extend(["", "## Dynamic parameters", ""])
    if report["parameters"]:
        for slot, values in report["parameters"].items():
            lines.append(f"- `{slot}`: " + ", ".join(
                f"{value} ({count})" for value, count in values.items()
            ))
    else:
        lines.append("- None observed.")
    lines.extend(["", "## Discovered catalog records without translation", ""])
    untranslated = [
        item for item in report["catalogDiscoveries"] if not item["translated"]
    ]
    if not untranslated:
        lines.append("No untranslated catalog records were discovered.")
    else:
        lines.extend(["| Record | Occurrences | Source |", "|---|---:|---|"])
        for item in untranslated:
            source = item["sourceText"].replace("|", "\\|").replace("\n", " / ")
            lines.append(
                f"| `{item['recordId']}` | {item['occurrences']} | {source} |"
            )
    lines.extend(["", "## Text candidates needing review", ""])
    review = [
        item for item in report["textCandidates"]
        if item["classification"] == "needs-review"
    ]
    if not review:
        lines.append("No new candidates were decoded.")
    else:
        lines.extend([
            "| Text | Occurrences | First example |",
            "|---|---:|---|",
        ])
        for item in review:
            example = item["example"]
            escaped = item["text"].replace("|", "\\|")
            lines.append(
                f"| {escaped} | {item['occurrences']} | frame {example['frame']}, "
                f"row {example['row']}, column {example['startColumn']} |"
            )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshots", required=True, type=Path)
    parser.add_argument("--text-runs", required=True, type=Path)
    parser.add_argument("--character-map", required=True, type=Path)
    parser.add_argument("--translations", required=True, type=Path)
    parser.add_argument("--vocabulary", required=True, type=Path)
    parser.add_argument("--dialogue-catalog", type=Path)
    parser.add_argument("--discoveries", type=Path)
    parser.add_argument("--json-output", required=True, type=Path)
    parser.add_argument("--markdown-output", required=True, type=Path)
    args = parser.parse_args()
    report = build_playtest_report(
        load_snapshots(args.snapshots), load_text_run_events(args.text_runs),
        load_character_map(args.character_map), _load_json(args.translations),
        _load_json(args.vocabulary),
        _load_json(args.dialogue_catalog) if args.dialogue_catalog else None,
        load_discovery_events(args.discoveries) if args.discoveries else (),
    )
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.markdown_output.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
