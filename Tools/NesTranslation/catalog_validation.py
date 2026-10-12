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
