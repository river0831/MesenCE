"""Generate a CHR-source-driven dialogue translation overlay for Mesen."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .database import DatabaseError, validate_rom, load_database


CONFIG_MARKER = "-- __NES_TRANSLATION_DIALOGUE_CONFIG__"


def _lua_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def load_translation_spec(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("formatVersion") != 1:
        raise DatabaseError("dialogue translation formatVersion must be 1")
    records = value.get("records")
    if not isinstance(records, list) or not records:
        raise DatabaseError("dialogue translation records must be a non-empty list")
    seen: set[str] = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise DatabaseError(f"records[{index}] must be an object")
        record_id = record.get("id")
        if not isinstance(record_id, str) or not record_id or record_id in seen:
            raise DatabaseError(f"invalid or duplicate dialogue record id: {record_id}")
        seen.add(record_id)
        lines = record.get("lines")
        if not isinstance(lines, list) or not lines or not all(
            isinstance(line, str) and line for line in lines
        ):
            raise DatabaseError(f"dialogue lines must be non-empty strings: {record_id}")
        box = record.get("box")
        if not isinstance(box, dict):
            raise DatabaseError(f"dialogue box must be an object: {record_id}")
        for key in ("x", "y", "width", "height", "lineHeight"):
            if not isinstance(box.get(key), int) or box[key] <= 0:
                raise DatabaseError(f"dialogue box.{key} must be positive: {record_id}")
    return value


def build_dialogue_config(catalog: dict[str, Any], spec: dict[str, Any]) -> str:
    catalog_by_id = {record["id"]: record for record in catalog.get("records", [])}
    runtime = spec.get("runtime")
    if not isinstance(runtime, dict):
        raise DatabaseError("dialogue translation runtime must be an object")
    required_runtime = (
        "chrStreamSelectorPc", "chrWindowSetupPc", "chrWindowWriterPc",
        "scratchFirstAddress", "visibilityStart", "visibilityEndExclusive",
        "clearWriteThreshold", "hideGraceFrames",
    )
    for key in required_runtime:
        if not isinstance(runtime.get(key), int) or runtime[key] < 0:
            raise DatabaseError(f"dialogue runtime.{key} must be non-negative")

    lines = [
        f"local chrStreamSelectorPc = {runtime['chrStreamSelectorPc']}",
        f"local chrWindowSetupPc = {runtime['chrWindowSetupPc']}",
        f"local chrWindowWriterPc = {runtime['chrWindowWriterPc']}",
        f"local scratchFirstAddress = {runtime['scratchFirstAddress']}",
        f"local visibilityStart = {runtime['visibilityStart']}",
        f"local visibilityEndExclusive = {runtime['visibilityEndExclusive']}",
        f"local clearWriteThreshold = {runtime['clearWriteThreshold']}",
        f"local hideGraceFrames = {runtime['hideGraceFrames']}",
        "local records = {",
    ]
    for translation in spec["records"]:
        record_id = translation["id"]
        source = catalog_by_id.get(record_id)
        if source is None:
            raise DatabaseError(f"translation references unknown catalog record: {record_id}")
        if source.get("runtime", {}).get("status") != "runtime-confirmed":
            raise DatabaseError(f"dialogue record is not runtime-confirmed: {record_id}")
        raw = list(bytes.fromhex(source["rawHex"]))
        box = translation["box"]
        lines.extend([
            "  {",
            f"    id = {_lua_string(record_id)},",
            "    raw = { " + ", ".join(str(value) for value in raw) + " },",
            "    lines = { "
            + ", ".join(_lua_string(line) for line in translation["lines"])
            + " },",
            f"    x = {box['x']}, y = {box['y']},",
            f"    width = {box['width']}, height = {box['height']},",
            f"    lineHeight = {box['lineHeight']},",
            "  },",
        ])
    lines.append("}")
    return "\n".join(lines)


def build_dialogue_overlay(
    catalog: dict[str, Any], spec: dict[str, Any], template: str
) -> str:
    if template.count(CONFIG_MARKER) != 1:
        raise ValueError("dialogue overlay template must contain exactly one config marker")
    return template.replace(CONFIG_MARKER, build_dialogue_config(catalog, spec))


def run_dialogue_overlay(
    mesen: Path,
    template_path: Path,
    rom_path: Path,
    game_database_path: Path,
    catalog_path: Path,
    translations_path: Path,
) -> int:
    database = load_database(game_database_path)
    validate_rom(database, rom_path)
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    if catalog.get("romSha256") != database.rom_sha256:
        raise DatabaseError("dialogue catalog does not match the bound ROM")
    spec = load_translation_spec(translations_path)
    script = build_dialogue_overlay(
        catalog, spec, template_path.read_text(encoding="utf-8")
    )
    with tempfile.TemporaryDirectory(prefix="nes-dialogue-overlay-") as folder:
        generated = Path(folder) / "dialogue-overlay.lua"
        generated.write_text(script, encoding="utf-8")
        print("Starting CHR dialogue translation overlay...", flush=True)
        with subprocess.Popen([
            str(mesen), "--enableStdout", "--doNotSaveSettings",
            str(generated), str(rom_path),
        ]) as process:
            return process.wait()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesen", required=True, type=Path)
    parser.add_argument("--template", required=True, type=Path)
    parser.add_argument("--rom", required=True, type=Path)
    parser.add_argument("--game-database", required=True, type=Path)
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--translations", required=True, type=Path)
    args = parser.parse_args()
    raise SystemExit(run_dialogue_overlay(
        args.mesen, args.template, args.rom, args.game_database,
        args.catalog, args.translations,
    ))


if __name__ == "__main__":
    main()
