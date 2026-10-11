"""Generate and launch a database-driven Mesen label overlay."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

from .database import DatabaseError, GameDatabase, load_database, validate_rom


CONFIG_MARKER = "-- __NES_TRANSLATION_CONFIG__"


def _lua_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def build_lua_config(database: GameDatabase) -> str:
    records = [record for record in database.records if record.presentation is not None]
    if not records:
        raise DatabaseError("database has no records with presentation data")

    lines = [
        f"local cpuAddressBase = {database.cpu_address_base}",
        f"local inputAddress = {database.input_address}",
        "local records = {",
    ]
    for record in records:
        assert record.presentation is not None
        end_address = database.cpu_address_base + record.prg_end_exclusive - 1
        start_address = database.cpu_address_base + record.prg_start
        if start_address > 0xFFFF or end_address > 0xFFFF:
            raise DatabaseError(f"presentation range does not fit CPU space: {record.id}")
        lines.extend([
            "  {",
            f"    id = {_lua_string(record.id)},",
            f"    startAddress = {start_address},",
            f"    endAddress = {end_address},",
            "    dismissInputMask = "
            + (str(record.dismiss_input_mask) if record.dismiss_input_mask else "nil")
            + ",",
            "    returnToRecordId = "
            + (_lua_string(record.return_to_record_id)
               if record.return_to_record_id else "nil")
            + ",",
            "    labels = {",
        ])
        for label in record.presentation.labels:
            lines.append(
                "      { text = %s, x = %d, y = %d, "
                "clearX = %d, clearY = %d, clearWidth = %d, clearHeight = %d },"
                % (
                    _lua_string(label.text), label.x, label.y,
                    label.clear.x, label.clear.y,
                    label.clear.width, label.clear.height,
                )
            )
        lines.extend(["    },", "  },"])
    lines.append("}")
    return "\n".join(lines)


def build_overlay_script(database: GameDatabase, template: str) -> str:
    if template.count(CONFIG_MARKER) != 1:
        raise ValueError("overlay template must contain exactly one config marker")
    return template.replace(CONFIG_MARKER, build_lua_config(database))


def run_overlay(
    mesen: Path,
    template_path: Path,
    rom_path: Path,
    database_path: Path,
) -> int:
    database = load_database(database_path)
    validate_rom(database, rom_path)
    script = build_overlay_script(
        database,
        template_path.read_text(encoding="utf-8"),
    )
    with tempfile.TemporaryDirectory(prefix="nes-translation-overlay-") as folder:
        generated_script = Path(folder) / "database-overlay.lua"
        generated_script.write_text(script, encoding="utf-8")
        command = [
            str(mesen),
            "--enableStdout",
            "--doNotSaveSettings",
            str(generated_script),
            str(rom_path),
        ]
        print("Starting database-driven Mesen overlay...", flush=True)
        with subprocess.Popen(command) as process:
            return process.wait()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesen", required=True, type=Path)
    parser.add_argument("--template", required=True, type=Path)
    parser.add_argument("--rom", required=True, type=Path)
    parser.add_argument("--database", required=True, type=Path)
    args = parser.parse_args()
    raise SystemExit(run_overlay(
        args.mesen,
        args.template,
        args.rom,
        args.database,
    ))


if __name__ == "__main__":
    main()
