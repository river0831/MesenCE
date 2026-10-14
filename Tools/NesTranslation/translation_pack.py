"""Load and validate a versioned per-ROM translation package."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any

from .database import DatabaseError, GameDatabase, load_database
from .text_review import load_character_map


SLOT_PATTERN = re.compile(r"\{([A-Z][A-Z0-9_]*)\}")


@dataclass(frozen=True)
class TranslationPack:
    id: str
    system: str
    locale: str
    rom_sha256: str
    database: GameDatabase
    character_map: dict[int, dict[str, Any]]
    dialogue_translations: dict[str, Any]
    vocabulary_translations: dict[str, Any]
    dictionary_catalog: dict[str, Any]
    paths: dict[str, Path]


def _object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DatabaseError(f"{context} must be an object")
    return value


def _string(value: dict[str, Any], key: str, context: str) -> str:
    result = value.get(key)
    if not isinstance(result, str) or not result:
        raise DatabaseError(f"{context}.{key} must be a non-empty string")
    return result


def _resolve_file(root: Path, files: dict[str, Any], key: str) -> Path:
    relative = Path(_string(files, key, "files"))
    if relative.is_absolute():
        raise DatabaseError(f"files.{key} must be relative to the package")
    resolved = (root / relative).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as error:
        raise DatabaseError(f"files.{key} escapes the package directory") from error
    if not resolved.is_file():
        raise DatabaseError(f"files.{key} does not exist: {relative}")
    return resolved


def _load_json(path: Path, context: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DatabaseError(f"cannot load {context}: {error}") from error
    return _object(value, context)


def _validate_segments(dialogue: dict[str, Any]) -> None:
    seen_ids: set[str] = set()
    for index, record in enumerate(dialogue.get("records", [])):
        record = _object(record, f"dialogue.records[{index}]")
        record_id = _string(record, "id", f"dialogue.records[{index}]")
        if record_id in seen_ids:
            raise DatabaseError(f"duplicate dialogue record id: {record_id}")
        seen_ids.add(record_id)
        previous_end = -1
        for segment_index, segment in enumerate(record.get("segments", [])):
            context = f"{record_id}.segments[{segment_index}]"
            segment = _object(segment, context)
            start = segment.get("sourceStart")
            end = segment.get("sourceEndExclusive")
            if (
                not isinstance(start, int) or not isinstance(end, int)
                or start < 0 or end <= start or start < previous_end
            ):
                raise DatabaseError(f"{context} has an invalid or overlapping range")
            previous_end = end


def _validate_runtime_parameters(dialogue: dict[str, Any]) -> None:
    for record in dialogue.get("records", []):
        runtime = record.get("runtimeComposition")
        if runtime is None:
            continue
        runtime = _object(runtime, f"{record.get('id')}.runtimeComposition")
        template = _string(runtime, "template", "runtimeComposition")
        parameters = _object(
            runtime.get("parameters"), "runtimeComposition.parameters"
        )
        slots = set(SLOT_PATTERN.findall(template))
        if slots != set(parameters):
            raise DatabaseError(
                f"{record.get('id')} template slots do not match parameter declarations"
            )
        for slot, raw_spec in parameters.items():
            spec = _object(raw_spec, f"{record.get('id')}.parameters.{slot}")
            if spec.get("source") != "preceding-vocabulary-term":
                raise DatabaseError(f"unsupported runtime parameter source: {slot}")
            categories = spec.get("categories")
            if (
                not isinstance(categories, list) or not categories
                or not all(isinstance(item, str) and item for item in categories)
            ):
                raise DatabaseError(f"runtime parameter categories are invalid: {slot}")
            if spec.get("selection") != "earliest-frame-last":
                raise DatabaseError(f"unsupported runtime parameter selection: {slot}")


def load_translation_pack(path: Path) -> TranslationPack:
    raw = _load_json(path, "translation pack")
    if raw.get("formatVersion") != 1:
        raise DatabaseError(
            f"unsupported translation pack formatVersion: {raw.get('formatVersion')}"
        )
    root = path.resolve().parent
    files = _object(raw.get("files"), "files")
    resolved_paths = {
        key: _resolve_file(root, files, key)
        for key in (
            "gameDatabase", "characterMap", "dialogueCatalog",
            "dialogueTranslations", "vocabularyTranslations",
            "dictionaryCatalog",
        )
    }
    database = load_database(resolved_paths["gameDatabase"])
    rom = _object(raw.get("rom"), "rom")
    rom_sha256 = _string(rom, "sha256", "rom").lower()
    if rom_sha256 != database.rom_sha256:
        raise DatabaseError("translation pack and game database ROM hashes differ")
    character_map = load_character_map(
        resolved_paths["characterMap"]
    )
    dialogue = _load_json(
        resolved_paths["dialogueTranslations"],
        "dialogue translations",
    )
    vocabulary = _load_json(
        resolved_paths["vocabularyTranslations"],
        "vocabulary translations",
    )
    dictionary_catalog = _load_json(
        resolved_paths["dictionaryCatalog"], "dictionary catalog"
    )
    _validate_segments(dialogue)
    _validate_runtime_parameters(dialogue)
    return TranslationPack(
        id=_string(raw, "id", "translation pack"),
        system=_string(raw, "system", "translation pack"),
        locale=_string(raw, "locale", "translation pack"),
        rom_sha256=rom_sha256,
        database=database,
        character_map=character_map,
        dialogue_translations=dialogue,
        vocabulary_translations=vocabulary,
        dictionary_catalog=dictionary_catalog,
        paths=resolved_paths,
    )
