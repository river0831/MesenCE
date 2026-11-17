"""Replay captured Nametable text runs through the production translation path."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

from .dialogue_glyph_provenance import SubtitleEventRouter
from .playtest_report import load_text_run_events
from .translation_pack import TranslationPack, load_translation_pack


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def replay_scenario(
    scenario_id: str,
    events: Iterable[dict[str, Any]],
    package: TranslationPack,
    dialogue_catalog: dict[str, Any],
    *,
    expected_record_ids: Iterable[str] = (),
    expected_texts: Iterable[str] = (),
    forbidden_texts: Iterable[str] = (),
) -> dict[str, Any]:
    """Replay one capture and compare its accumulated output with expectations."""
    router = SubtitleEventRouter(
        package.dialogue_translations,
        package.database,
        package.vocabulary_translations,
        package.dictionary_catalog,
        dialogue_catalog,
        package.character_map,
    )
    event_count = 0
    frames: set[int] = set()
    snapshots: list[dict[str, Any]] = []
    record_ids: set[str] = set()
    texts: set[str] = set()
    duplicate_snapshots: list[int] = []
    for event in events:
        event_count += 1
        if isinstance(event.get("frame"), int):
            frames.add(event["frame"])
        scene = router.consume(
            "DQRUN " + json.dumps(event, ensure_ascii=False, separators=(",", ":"))
        )
        if scene is None:
            continue
        snapshots.append(scene)
        unit_ids = [
            str(item.get("unitId", "")) for item in scene.get("items", [])
        ]
        if len(unit_ids) != len(set(unit_ids)):
            duplicate_snapshots.append(int(scene.get("frame", 0)))
        for item in scene.get("items", []):
            if isinstance(item.get("recordId"), str):
                record_ids.add(item["recordId"])
            if isinstance(item.get("text"), str):
                texts.add(item["text"])

    expected_record_ids = set(expected_record_ids)
    expected_texts = set(expected_texts)
    forbidden_texts = set(forbidden_texts)
    missing_records = sorted(expected_record_ids - record_ids)
    missing_texts = sorted(expected_texts - texts)
    unexpected_texts = sorted(forbidden_texts & texts)
    errors = []
    if missing_records:
        errors.append("missing-records")
    if missing_texts:
        errors.append("missing-texts")
    if unexpected_texts:
        errors.append("forbidden-texts")
    if duplicate_snapshots:
        errors.append("duplicate-units")
    return {
        "id": scenario_id,
        "status": "pass" if not errors else "fail",
        "eventCount": event_count,
        "frameCount": len(frames),
        "snapshotCount": len(snapshots),
        "observedRecordIds": sorted(record_ids),
        "observedTexts": sorted(texts),
        "missingRecordIds": missing_records,
        "missingTexts": missing_texts,
        "forbiddenTextsObserved": unexpected_texts,
        "duplicateUnitFrames": sorted(set(duplicate_snapshots)),
        "errors": errors,
    }


def run_manifest(
    manifest_path: Path, package_path: Path | None = None,
) -> dict[str, Any]:
    manifest = _load_json(manifest_path)
    package_value = package_path or (
        manifest_path.parent / str(manifest["translationPack"])
    ).resolve()
    package = load_translation_pack(package_value)
    dialogue_catalog = _load_json(package.paths["dialogueCatalog"])
    scenarios = []
    for raw in manifest.get("scenarios", []):
        source = (manifest_path.parent / str(raw["textRuns"])).resolve()
        scenarios.append(replay_scenario(
            str(raw["id"]),
            load_text_run_events(source),
            package,
            dialogue_catalog,
            expected_record_ids=raw.get("expectedRecordIds", []),
            expected_texts=raw.get("expectedTexts", []),
            forbidden_texts=raw.get("forbiddenTexts", []),
        ))
    return {
        "summary": {
            "scenarioCount": len(scenarios),
            "passed": sum(item["status"] == "pass" for item in scenarios),
            "failed": sum(item["status"] == "fail" for item in scenarios),
        },
        "scenarios": scenarios,
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Captured scenario regression",
        "",
        f"- Scenarios: {summary['scenarioCount']}",
        f"- Passed: {summary['passed']}",
        f"- Failed: {summary['failed']}",
        "",
        "| Scenario | Status | Events | Frames | Snapshots | Records |",
        "|---|---|---:|---:|---:|---|",
    ]
    for item in report["scenarios"]:
        records = ", ".join(f"`{value}`" for value in item["observedRecordIds"])
        lines.append(
            f"| `{item['id']}` | {item['status']} | {item['eventCount']} | "
            f"{item['frameCount']} | {item['snapshotCount']} | {records or '—'} |"
        )
        if item["errors"]:
            lines.append(
                f"|  | Errors: {', '.join(item['errors'])} |  |  |  |  |"
            )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--translation-pack", type=Path)
    parser.add_argument("--json-output", required=True, type=Path)
    parser.add_argument("--markdown-output", required=True, type=Path)
    args = parser.parse_args()
    report = run_manifest(args.manifest, args.translation_pack)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.markdown_output.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    if report["summary"]["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
