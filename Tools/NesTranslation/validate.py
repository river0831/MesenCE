"""Validate the PoC database schema and its byte identity against the ROM."""

from __future__ import annotations

import argparse
from pathlib import Path

from .database import load_database, validate_rom


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("database", type=Path)
    parser.add_argument("rom", type=Path)
    args = parser.parse_args()
    database = load_database(args.database)
    validate_rom(database, args.rom)
    print(f"OK: {len(database.records)} record(s), ROM SHA-256 matched")


if __name__ == "__main__":
    main()
