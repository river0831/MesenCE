"""Merge all static ROM text candidates into a Chinese review catalog.

The exporter deliberately preserves low-confidence records.  Extraction and
translation are separate decisions: a byte range can be losslessly listed
without pretending that it is human language or that its draft is final.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any


def _load_records(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8")).get("records", [])


def _translation_index(*paths: Path | None) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for path in paths:
        if path is None:
            continue
        for item in _load_records(path):
            if isinstance(item, dict) and isinstance(item.get("id"), str):
                result[item["id"]] = item
    return result


def classify_dialogue(text: str, likelihood: str) -> tuple[str, str]:
    if likelihood == "low":
        return "uncertain-or-graphics", "low static likelihood; retained losslessly"
    if any(term in text for term in ("こうげき", "たおした", "あらわれた", "にげだした", "ねむって", "ほのおをはいた")):
        return "battle", "battle action/result vocabulary"
    if any(term in text for term in ("てにいれた", "みつけた", "たからのはこ", "なにを すて", "もてない", "からっ")):
        return "chest-or-system", "inventory/chest result vocabulary"
    if any(term in text for term in ("いらっしゃい", "かうかね", "おもとめ", "おうり", "おかねが", "やどや", "おやすみ")):
        return "shop-or-inn", "shop/inn interaction vocabulary"
    if any(term in text for term in ("じゅもん", "たいまつ", "せいすい", "つばさ", "うろこ", "ゆびわ", "たてごと")) and "＊「" not in text:
        return "item-spell-action", "item/spell use vocabulary"
    if any(term in text for term in ("りゅうおう", "ひかりのたま", "へいわが もど", "ばんざい", "せきばん")) and len(text) > 80:
        return "story-or-ending", "long story/ending vocabulary"
    if "＊「" in text or "「" in text:
        return "npc-dialogue", "speaker marker"
    if any(marker in text for marker in ("{PLAYER_NAME}", "<FD>", "<F3>")):
        return "dynamic-template", "runtime placeholder/control marker"
    return "system-or-unknown", "no stronger semantic heuristic"


def build_catalog(
    dialogue: dict[str, Any],
    dictionary: dict[str, Any],
    translations: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for source in dialogue.get("records", []):
        likelihood = source.get("evidence", {}).get("likelihood", "unknown")
        category, reason = classify_dialogue(str(source.get("decoded", "")), likelihood)
        translated = translations.get(str(source.get("id")))
        records.append({
            "id": source.get("id"),
            "kind": "chr-record",
            "category": translated.get("category", category) if translated else category,
            "categoryEvidence": reason,
            "sourceText": source.get("decoded", ""),
            "translation": translated.get("translation") if translated else None,
            "translationStatus": (
                translated.get("translationStatus", "reviewed") if translated else "pending"
            ),
            "staticLikelihood": likelihood,
            "unknownBytes": source.get("unknownBytes", []),
            "source": source.get("source"),
            "rawHex": source.get("rawHex"),
        })
    for source in dictionary.get("entries", []):
        translated = translations.get(str(source.get("id")))
        records.append({
            "id": source.get("id"),
            "kind": "prg-dictionary-entry",
            "category": translated.get("category", source.get("suggestedCategory", "phrase")) if translated else source.get("suggestedCategory", "phrase"),
            "categoryEvidence": source.get("categoryEvidence"),
            "sourceText": source.get("normalized", source.get("decoded", "")),
            "translation": translated.get("translation") if translated else None,
            "translationStatus": (
                translated.get("translationStatus", "reviewed") if translated else "pending"
            ),
            "staticLikelihood": "dictionary-entry",
            "unknownBytes": source.get("unknownBytes", []),
            "source": {
                "section": "PRG",
                "prgStart": source.get("prgStart"),
                "prgEndExclusive": source.get("prgEndExclusive"),
                "token": source.get("token"),
            },
            "rawHex": source.get("rawHex"),
        })
    counts = Counter(str(record["category"]) for record in records)
    statuses = Counter(str(record["translationStatus"]) for record in records)
    return {
        "formatVersion": 1,
        "language": "zh-Hans",
        "romSha256": dialogue.get("romSha256"),
        "policy": {
            "preservesEveryExtractedCandidate": True,
            "translationIsIndependentFromExtraction": True,
            "lowConfidenceMayBeGraphics": True,
        },
        "summary": {
            "recordCount": len(records),
            "chrRecordCount": len(dialogue.get("records", [])),
            "dictionaryEntryCount": len(dictionary.get("entries", [])),
            "byCategory": dict(sorted(counts.items())),
            "byTranslationStatus": dict(sorted(statuses.items())),
        },
        "records": records,
    }


def render_markdown(catalog: dict[str, Any]) -> str:
    summary = catalog["summary"]
    lines = [
        "# Dragon Quest 原 ROM 文本全量提取与中文审阅目录",
        "",
        f"- ROM SHA-256: `{catalog['romSha256']}`",
        f"- 总记录：**{summary['recordCount']}**（CHR `$FC` 候选 {summary['chrRecordCount']}；PRG 词典 {summary['dictionaryEntryCount']}）",
        "- `reviewed`：现有运行时数据库已采用；`draft`：本轮人工草译；`pending`：保留原文，尚未可靠翻译。",
        "- `uncertain-or-graphics` 不代表台词：它们是为保证“尽可能多提取”而保留的低可信字节记录。",
        "",
        "## 文本类型概览",
        "",
    ]
    for category, count in summary["byCategory"].items():
        lines.append(f"- `{category}`：{count}")
    lines.extend(["", "## 翻译进度", ""])
    for status, count in summary["byTranslationStatus"].items():
        lines.append(f"- `{status}`：{count}")
    lines.extend(["", "## 可读文本（高/中可信 CHR 与全部 PRG 词典）", ""])
    for record in catalog["records"]:
        if record["kind"] == "chr-record" and record["staticLikelihood"] == "low":
            continue
        source = record["source"] or {}
        if record["kind"] == "chr-record":
            location = f"CHR `${source.get('chrStart', 0):04X}` / file `${source.get('fileStart', 0):04X}`"
        else:
            location = f"PRG `${source.get('prgStart', 0):04X}` / token `${source.get('token', 0):02X}`"
        translation = record["translation"] or "（待翻译/待确认）"
        text = str(record["sourceText"]).rstrip().replace("\n", " / ")
        lines.extend([
            f"### {record['id']} · `{record['category']}` · `{record['translationStatus']}`",
            "",
            f"- 位置：{location}",
            f"- 原文：{text}",
            f"- 中文：{translation}",
            "",
        ])
    lines.extend([
        "## 低可信候选",
        "",
        "低可信记录完整保存在同名 JSON 的 `records` 中；Markdown 不逐条展开，以免把 CHR 图形字节误导为日文文本。",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dialogue-catalog", required=True, type=Path)
    parser.add_argument("--dictionary-catalog", required=True, type=Path)
    parser.add_argument("--dialogue-translations", required=True, type=Path)
    parser.add_argument("--vocabulary-translations", required=True, type=Path)
    parser.add_argument("--draft-translations", required=True, type=Path)
    parser.add_argument("--json-output", required=True, type=Path)
    parser.add_argument("--markdown-output", required=True, type=Path)
    args = parser.parse_args()
    dialogue = json.loads(args.dialogue_catalog.read_text(encoding="utf-8"))
    dictionary = json.loads(args.dictionary_catalog.read_text(encoding="utf-8"))
    translations = _translation_index(
        args.dialogue_translations, args.vocabulary_translations, args.draft_translations
    )
    catalog = build_catalog(dialogue, dictionary, translations)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown_output.write_text(render_markdown(catalog), encoding="utf-8")
    print(json.dumps(catalog["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
