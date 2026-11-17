#!/usr/bin/env python3
"""Extract the decoded Japanese text from the Fire Emblem Gaiden disassembly.

The upstream disassembly has already identified text-bearing byte ranges and
decoded their character/control-code format.  This tool deliberately emits
both lossless string segments and conservative message records: a consumer can
use the records immediately without losing strings whose exact grouping is not
yet known.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path


STRING_RE = re.compile(r'^\s*\.STRINGMAP\s+script_jp,\s*("(?:[^"\\]|\\.)*")')
LABEL_RE = re.compile(r"^\s*(L[0-9A-Fa-f]{6}|[A-Za-z_][A-Za-z0-9_]*):")
CONTROL_RE = re.compile(r"^\s*(PAGE|SPEAK|NEWLINE|WAIT_CLICK)(?:\s|$)")
ARG_CONTROL_RE = re.compile(r"^\s*(FACE|NAME)\s+([^;]+)")
STOP_RE = re.compile(r"^\s*\.db\s+STOP(?:\s|$)")
ASM_RE = re.compile(r"^\s*(?:\.[A-Za-z]+|[A-Z]{3})(?:\s|$)")


@dataclass
class Record:
    bank: str
    label: str | None
    start_line: int
    end_line: int
    segments: list[dict] = field(default_factory=list)
    events: list[dict] = field(default_factory=list)
    terminated: bool = False

    @property
    def text(self) -> str:
        output: list[str] = []
        for event in self.events:
            kind = event["kind"]
            if kind == "text":
                output.append(event["text"])
            elif kind in {"NEWLINE", "PAGE"}:
                output.append("\n")
            elif kind == "WAIT_CLICK":
                output.append("{wait}")
            elif kind in {"FACE", "NAME", "SPEAK"}:
                arg = event.get("argument")
                output.append("{" + kind.lower() + (":" + arg if arg else "") + "}")
        return "".join(output)


def _decode_quoted(value: str) -> str:
    # Assembly strings in this source use JSON-compatible quoting for the
    # decoded Japanese text.
    return json.loads(value)


def extract(source_dir: Path) -> tuple[list[dict], list[dict]]:
    segments: list[dict] = []
    records: list[Record] = []

    for asm_path in sorted(source_dir.glob("bank*.asm")):
        bank = asm_path.stem
        lines = asm_path.read_text(encoding="utf-8").splitlines()
        current_label: str | None = None
        record: Record | None = None
        foreign_code_after_text = False

        def finish(end_line: int, terminated: bool = False) -> None:
            nonlocal record, foreign_code_after_text
            if record and record.segments:
                record.end_line = end_line
                record.terminated = terminated
                records.append(record)
            record = None
            foreign_code_after_text = False

        for line_no, line in enumerate(lines, 1):
            stripped = line.strip()
            label_match = LABEL_RE.match(line)
            if label_match:
                current_label = label_match.group(1)
                # A new entry point following executable/data statements is a
                # safe boundary. Labels inside a dialogue remain in one record.
                if record and foreign_code_after_text:
                    finish(line_no - 1)
                continue

            string_match = STRING_RE.match(line)
            if string_match:
                if record and foreign_code_after_text:
                    finish(line_no - 1)
                if record is None:
                    record = Record(bank, current_label, line_no, line_no)
                text = _decode_quoted(string_match.group(1))
                segment = {
                    "id": f"{bank}-line-{line_no}",
                    "bank": bank,
                    "label": current_label,
                    "sourceLine": line_no,
                    "text": text,
                }
                segments.append(segment)
                record.segments.append(segment)
                record.events.append({"kind": "text", "text": text, "sourceLine": line_no})
                record.end_line = line_no
                foreign_code_after_text = False
                continue

            if record is None:
                continue
            if STOP_RE.match(line):
                record.events.append({"kind": "STOP", "sourceLine": line_no})
                finish(line_no, terminated=True)
                continue
            control_match = CONTROL_RE.match(line)
            if control_match:
                record.events.append({"kind": control_match.group(1), "sourceLine": line_no})
                record.end_line = line_no
                continue
            arg_match = ARG_CONTROL_RE.match(line)
            if arg_match:
                record.events.append(
                    {"kind": arg_match.group(1), "argument": arg_match.group(2).strip(), "sourceLine": line_no}
                )
                record.end_line = line_no
                continue
            if not stripped or stripped.startswith(";"):
                continue
            if ASM_RE.match(line):
                foreign_code_after_text = True

        finish(len(lines))

    output_records = []
    for index, record in enumerate(records):
        output_records.append(
            {
                "id": f"fe2-{index:04d}",
                "bank": record.bank,
                "label": record.label,
                "sourceLineStart": record.start_line,
                "sourceLineEnd": record.end_line,
                "terminatedByStop": record.terminated,
                "text": record.text,
                "segments": [item["id"] for item in record.segments],
                "events": record.events,
            }
        )
    return segments, output_records


def sha1(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_character_table(path: Path) -> list[dict]:
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith(";") or "=" not in line:
            continue
        encoded, text = line.split("=", 1)
        entries.append(
            {
                "bytes": [encoded[index : index + 2] for index in range(0, len(encoded), 2)],
                "text": text,
                "kind": "template" if text.startswith("%") else "glyph",
            }
        )
    return entries


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True, help="Directory containing bank*.asm")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--rom", type=Path)
    args = parser.parse_args()

    segments, records = extract(args.source_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    provenance = {
        "formatVersion": 1,
        "game": "Fire Emblem Gaiden (Japan)",
        "method": "decoded-disassembly",
        "source": "https://github.com/minirop/fe2",
        "sourceCommit": "956365ef33c63751e7afd03f05e600d7728549da",
        "sourceBuildSha1": "2153ae9a7b1c63e8d4d83a807f1c8c1f482f7293",
        "localRomSha1": sha1(args.rom) if args.rom else None,
        "limitations": [
            "The local PRG checksum differs from the disassembly build checksum.",
            "CHR data matches exactly; extracted text should still be verified against runtime screens.",
            "Conservative records without STOP may represent labels, menus, or other standalone strings.",
        ],
    }
    (args.output_dir / "text-segments.json").write_text(
        json.dumps({**provenance, "count": len(segments), "segments": segments}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "message-records.json").write_text(
        json.dumps({**provenance, "count": len(records), "records": records}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    table_path = args.source_dir.parent / "jp.tbl"
    if table_path.exists():
        character_table = read_character_table(table_path)
        (args.output_dir / "character-table.json").write_text(
            json.dumps(
                {**provenance, "count": len(character_table), "entries": character_table},
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    review = [
        "# Fire Emblem Gaiden extracted text",
        "",
        f"- String segments: {len(segments)}",
        f"- Conservative records: {len(records)}",
        f"- STOP-terminated records: {sum(bool(item['terminatedByStop']) for item in records)}",
        "",
    ]
    for item in records:
        review.extend((f"## {item['id']} — {item['bank']}:{item['label'] or 'unlabelled'}", "", item["text"], ""))
    (args.output_dir / "message-records.md").write_text("\n".join(review), encoding="utf-8")
    print(f"Extracted {len(segments)} segments into {len(records)} conservative records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
