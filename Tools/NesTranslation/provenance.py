"""Generate a lightweight Nametable provenance trace for Mesen."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

from .database import DatabaseError, GameDatabase, load_database, validate_rom


CONFIG_MARKER = "-- __NES_TRANSLATION_PROVENANCE_CONFIG__"


def _lua_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def build_lua_config(database: GameDatabase, source_ttl_frames: int = 3) -> str:
    if source_ttl_frames < 0:
        raise ValueError("source TTL must be non-negative")
    if not database.records:
        raise DatabaseError("database has no text records")

    lines = [f"local sourceTtlFrames = {source_ttl_frames}", "local records = {"]
    for record in database.records:
        start_address = database.cpu_address_base + record.prg_start
        end_address = database.cpu_address_base + record.prg_end_exclusive - 1
        if start_address > 0xFFFF or end_address > 0xFFFF:
            raise DatabaseError(f"record range does not fit CPU space: {record.id}")
        lines.append(
            "  { id = %s, startAddress = %d, endAddress = %d },"
            % (_lua_string(record.id), start_address, end_address)
        )
    lines.append("}")
    buffer = database.ppu_update_buffer
    if buffer is None:
        lines.append("local ppuUpdateBuffer = nil")
    else:
        lines.extend([
            "local ppuUpdateBuffer = {",
            f"  ramStart = {buffer.ram_start},",
            f"  ramEndExclusive = {buffer.ram_end_exclusive},",
            f"  entrySize = {buffer.entry_size},",
            f"  addressHighOffset = {buffer.address_high_offset},",
            f"  addressLowOffset = {buffer.address_low_offset},",
            f"  valueOffset = {buffer.value_offset},",
            "}",
        ])
    return "\n".join(lines)


def build_provenance_script(
    database: GameDatabase,
    template: str,
    source_ttl_frames: int = 3,
) -> str:
    if template.count(CONFIG_MARKER) != 1:
        raise ValueError("provenance template must contain exactly one config marker")
    return template.replace(
        CONFIG_MARKER, build_lua_config(database, source_ttl_frames)
    )


def run_provenance(
    mesen: Path,
    template_path: Path,
    rom_path: Path,
    database_path: Path,
    source_ttl_frames: int,
) -> int:
    database = load_database(database_path)
    validate_rom(database, rom_path)
    script = build_provenance_script(
        database, template_path.read_text(encoding="utf-8"), source_ttl_frames
    )
    with tempfile.TemporaryDirectory(prefix="nes-translation-provenance-") as folder:
        generated_script = Path(folder) / "nametable-provenance.lua"
        generated_script.write_text(script, encoding="utf-8")
        command = [
            str(mesen), "--enableStdout", "--doNotSaveSettings",
            str(generated_script), str(rom_path),
        ]
        print("Starting Nametable provenance prototype...", flush=True)
        with subprocess.Popen(command) as process:
            return process.wait()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesen", required=True, type=Path)
    parser.add_argument("--template", required=True, type=Path)
    parser.add_argument("--rom", required=True, type=Path)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--source-ttl-frames", type=int, default=3)
    args = parser.parse_args()
    raise SystemExit(run_provenance(
        args.mesen, args.template, args.rom, args.database, args.source_ttl_frames
    ))


if __name__ == "__main__":
    main()
