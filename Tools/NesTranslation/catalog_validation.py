"""Merge exact runtime dialogue matches into a generated static catalog."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any, Iterable


def apply_runtime_matches(
    catalog: dict[str, Any], match_reports: Iterable[dict[str, Any]]
) -> dict[str, Any]:
    result = copy.deepcopy(catalog)
    reports = list(match_reports)
    by_id = {record["id"]: record for record in result.get("records", [])}
    observations: dict[str, list[dict[str, Any]]] = {}
    for report in reports:
        trace = report.get("trace")
        for hit in report.get("hits", []):
            record_id = hit["recordId"]
            if record_id not in by_id:
                raise ValueError(f"runtime match references unknown record: {record_id}")
            observations.setdefault(record_id, []).append({
                "trace": trace,
                "frameStart": hit["frameStart"],
                "frameEnd": hit["frameEnd"],
                "selector": hit["selector"],
                "ppuStart": hit["ppuStart"],
                "ppuEndExclusive": hit["ppuEndExclusive"],
            })

    for record_id, items in observations.items():
        runtime = by_id[record_id]["runtime"]
        runtime["status"] = "runtime-confirmed"
        runtime["occurrenceCount"] = len(items)
        runtime["observations"] = items
        runtime["observedReadAddress"] = items[0]["ppuStart"]
        runtime["notes"] = "Exact raw-byte match from overlapping CHR staging windows"

    result["validationSummary"] = {
        "reportCount": len(reports),
        "runtimeConfirmedRecordCount": len(observations),
        "runtimeOccurrenceCount": sum(len(items) for items in observations.values()),
    }
    return result


def apply_runtime_discoveries(
    catalog: dict[str, Any], events: Iterable[dict[str, Any]], *, trace: str
) -> dict[str, Any]:
    """Promote records matched byte-for-byte by the live catalog trie."""
    result = copy.deepcopy(catalog)
    by_id = {record["id"]: record for record in result.get("records", [])}
    observations: dict[str, list[int]] = {}
    for event in events:
        if event.get("type") != "catalog-record":
            continue
        record_id = event.get("recordId")
        frame = event.get("frame")
        if record_id not in by_id:
            raise ValueError(f"runtime discovery references unknown record: {record_id}")
        if not isinstance(frame, int):
            raise ValueError(f"runtime discovery has invalid frame: {record_id}")
        observations.setdefault(str(record_id), []).append(frame)
    for record_id, frames in observations.items():
        runtime = by_id[record_id]["runtime"]
        previous = list(runtime.get("observations", []))
        known = {
            (item.get("trace"), item.get("frame"))
            for item in previous
            if isinstance(item, dict) and "frame" in item
        }
        previous.extend(
            {"trace": trace, "frame": frame}
            for frame in dict.fromkeys(frames)
            if (trace, frame) not in known
        )
        runtime["status"] = "runtime-confirmed"
        runtime["occurrenceCount"] = len(previous)
        runtime["observations"] = previous
        runtime["notes"] = "Exact full-record match from runtime catalog trie"
    result["discoveryValidationSummary"] = {
        "trace": trace,
        "runtimeConfirmedRecordCount": len(observations),
        "runtimeOccurrenceCount": sum(len(items) for items in observations.values()),
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--matches", required=True, action="append", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    reports = [json.loads(path.read_text(encoding="utf-8")) for path in args.matches]
    validated = apply_runtime_matches(catalog, reports)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(validated, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    summary = validated["validationSummary"]
    print(
        f"Validated {summary['runtimeConfirmedRecordCount']} distinct records "
        f"across {summary['runtimeOccurrenceCount']} occurrences"
    )


if __name__ == "__main__":
    main()
