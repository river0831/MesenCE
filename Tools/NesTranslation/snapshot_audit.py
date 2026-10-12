"""Audit recorded visible-translation snapshots for lifecycle/layout defects."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .snapshot_replay import load_snapshots


@dataclass(frozen=True)
class AuditFinding:
    severity: str
    code: str
    frame: int
    unit_ids: tuple[str, ...]
    message: str


def _overlap(first: dict[str, int], second: dict[str, int]) -> bool:
    return (
        first["x"] < second["x"] + second["width"]
        and second["x"] < first["x"] + first["width"]
        and first["y"] < second["y"] + second["height"]
        and second["y"] < first["y"] + first["height"]
    )


def audit_snapshots(
    snapshots: list[dict[str, Any]],
    *,
    flicker_frames: int = 4,
    lingering_frames: int = 1800,
) -> dict[str, Any]:
    if flicker_frames < 0 or lingering_frames <= 0:
        raise ValueError("audit frame thresholds must be positive")
    findings: list[AuditFinding] = []
    previous: dict[str, dict[str, Any]] = {}
    appeared_at: dict[str, int] = {}
    disappeared_at: dict[str, int] = {}
    seen_records: set[str] = set()
    previous_overlaps: set[tuple[str, str]] = set()

    def report(
        severity: str, code: str, frame: int, unit_ids: tuple[str, ...], message: str
    ) -> None:
        findings.append(AuditFinding(severity, code, frame, unit_ids, message))

    for snapshot in snapshots:
        frame = snapshot["frame"]
        items = snapshot["items"]
        current: dict[str, dict[str, Any]] = {}
        for item in items:
            unit_id = item.get("unitId")
            if not isinstance(unit_id, str) or not unit_id:
                report("error", "invalid-unit-id", frame, (), "item has no stable unitId")
                continue
            if unit_id in current:
                report("error", "duplicate-unit", frame, (unit_id,),
                       "unitId occurs more than once in one snapshot")
                continue
            current[unit_id] = item
            if isinstance(item.get("recordId"), str):
                seen_records.add(item["recordId"])
            bounds = item.get("ppuBounds")
            if not isinstance(bounds, dict) or not all(
                isinstance(bounds.get(key), int)
                for key in ("x", "y", "width", "height")
            ):
                report("error", "invalid-bounds", frame, (unit_id,),
                       "PPU bounds are missing or non-integer")
            elif (
                bounds["width"] <= 0 or bounds["height"] <= 0
                or bounds["x"] < 0 or bounds["y"] < 0
                or bounds["x"] + bounds["width"] > 256
                or bounds["y"] + bounds["height"] > 240
            ):
                report("error", "out-of-bounds", frame, (unit_id,),
                       "PPU bounds exceed the 256x240 viewport")
            visible = item.get("visibleCount")
            total = item.get("totalCount")
            ratio = item.get("visibleRatio")
            if (
                not isinstance(visible, int) or not isinstance(total, int)
                or total <= 0 or visible <= 0
                or not isinstance(ratio, (int, float)) or not 0 <= ratio <= 1
                or abs(ratio - min(visible / total, 1.0)) > 1e-9
            ):
                report("error", "invalid-coverage", frame, (unit_id,),
                       "visibility count, total, and ratio are inconsistent")

        unit_ids = sorted(current)
        current_overlaps: set[tuple[str, str]] = set()
        for index, first_id in enumerate(unit_ids):
            first_bounds = current[first_id].get("ppuBounds")
            if not isinstance(first_bounds, dict):
                continue
            for second_id in unit_ids[index + 1:]:
                second_bounds = current[second_id].get("ppuBounds")
                if isinstance(second_bounds, dict) and _overlap(first_bounds, second_bounds):
                    current_overlaps.add((first_id, second_id))
        for pair in sorted(current_overlaps - previous_overlaps):
            report("warning", "overlap", frame, pair,
                   "visible translation rectangles began to overlap")
        previous_overlaps = current_overlaps

        expected_delta = {
            "appeared": sorted(current.keys() - previous.keys()),
            "updated": sorted(
                key for key in current.keys() & previous.keys()
                if current[key] != previous[key]
            ),
            "disappeared": sorted(previous.keys() - current.keys()),
        }
        if snapshot.get("delta") != expected_delta:
            report("error", "delta-mismatch", frame, (),
                   "snapshot delta does not match consecutive item states")
        for unit_id in expected_delta["appeared"]:
            last_gone = disappeared_at.get(unit_id)
            if last_gone is not None and frame - last_gone <= flicker_frames:
                report("warning", "flicker", frame, (unit_id,),
                       f"unit reappeared after {frame - last_gone} frames")
            appeared_at[unit_id] = frame
        for unit_id in expected_delta["disappeared"]:
            start = appeared_at.pop(unit_id, frame)
            disappeared_at[unit_id] = frame
            if frame - start >= lingering_frames:
                report("warning", "long-lived", frame, (unit_id,),
                       f"unit remained visible for {frame - start} frames")
        previous = current

    if previous:
        final_frame = snapshots[-1]["frame"]
        report("warning", "visible-at-end", final_frame, tuple(sorted(previous)),
               "trace ended while translation units were still visible")

    serialized = [asdict(finding) for finding in findings]
    return {
        "snapshotCount": len(snapshots),
        "firstFrame": snapshots[0]["frame"],
        "lastFrame": snapshots[-1]["frame"],
        "recordIds": sorted(seen_records),
        "summary": {
            "errors": sum(item["severity"] == "error" for item in serialized),
            "warnings": sum(item["severity"] == "warning" for item in serialized),
        },
        "findings": serialized,
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Translation Snapshot Audit",
        "",
        f"- Snapshots: {report['snapshotCount']}",
        f"- Frames: {report['firstFrame']}–{report['lastFrame']}",
        f"- Errors: {summary['errors']}",
        f"- Warnings: {summary['warnings']}",
        f"- Records: {', '.join(report['recordIds']) or '(none)'}",
        "",
        "## Findings",
        "",
    ]
    if not report["findings"]:
        lines.append("No issues found.")
    else:
        for finding in report["findings"]:
            units = ", ".join(finding["unit_ids"]) or "snapshot"
            lines.append(
                f"- **{finding['severity'].upper()} `{finding['code']}`** "
                f"frame {finding['frame']} ({units}): {finding['message']}"
            )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace", required=True, type=Path)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    parser.add_argument("--flicker-frames", type=int, default=4)
    parser.add_argument("--lingering-frames", type=int, default=1800)
    args = parser.parse_args()
    report = audit_snapshots(
        load_snapshots(args.trace),
        flicker_frames=args.flicker_frames,
        lingering_frames=args.lingering_frames,
    )
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    markdown = render_markdown(report)
    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(markdown, encoding="utf-8")
    if not args.json_output and not args.markdown_output:
        print(markdown, end="")
    raise SystemExit(1 if report["summary"]["errors"] else 0)


if __name__ == "__main__":
    main()
