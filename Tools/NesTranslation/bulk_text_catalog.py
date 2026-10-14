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
import re
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


SAFE_LAYOUT_CODES = {"4F", "50", "52", "57", "60", "6C", "FB", "FF", "END"}


def assess_display_difficulty(
    text: str, likelihood: str, unknown_bytes: list[int], *, kind: str,
    source_offset: int | None = None,
) -> tuple[str, str]:
    """Estimate overlay difficulty from source mechanics, never from semantics."""
    if likelihood == "low":
        return "hard", "low-confidence extraction may be CHR graphics"
    if kind == "chr-record" and source_offset is not None and source_offset >= 0x5000:
        return "hard", "late CHR range behaves like tiles/graphics rather than dialogue"
    if kind == "prg-dictionary-entry":
        if unknown_bytes or not text:
            return "hard", "dictionary entry is empty or contains unresolved bytes"
        return "easy", "fixed dictionary text with a stable token"
    if any(marker in text for marker in ("{PLAYER_NAME}", "<FD>", "<F3>")):
        return "hard", "contains a runtime-substituted name, object, enemy, or number"
    codes = set(re.findall(r"<([0-9A-F]{2}|END)>", text))
    unresolved = sorted(codes - SAFE_LAYOUT_CODES)
    if unresolved:
        return "hard", "contains unresolved source bytes or non-layout controls"
    visible = re.sub(r"<[^>]+>|[＊「／\n]", "", text)
    page_breaks = text.count("<57>") + text.count("<FF>")
    if len(visible) > 72 or page_breaks > 1:
        return "medium", "fixed text, but long or split across several dialogue pages"
    return "easy", "short fixed text with only understood layout controls"


def build_catalog(
    dialogue: dict[str, Any],
    dictionary: dict[str, Any],
    translations: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for source in dialogue.get("records", []):
        likelihood = source.get("evidence", {}).get("likelihood", "unknown")
        category, reason = classify_dialogue(str(source.get("decoded", "")), likelihood)
        difficulty, difficulty_reason = assess_display_difficulty(
            str(source.get("decoded", "")), likelihood,
            source.get("unknownBytes", []), kind="chr-record",
            source_offset=source.get("source", {}).get("chrStart"),
        )
        translated = translations.get(str(source.get("id")))
        translated_units = {
            str(item.get("id")): item
            for item in (translated or {}).get("units", [])
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        source_units = source.get("messageUnits") or [{
            "id": f"{source.get('id')}-u1",
            "ordinal": 1,
            "source": {**(source.get("source") or {}), "containerId": source.get("id")},
            "rawHex": source.get("rawHex"),
            "expandedHex": source.get("expandedHex"),
            "decoded": source.get("decoded", ""),
            "separatorHex": "",
            "boundaryConfidence": "legacy-container",
        }]
        message_units = []
        for unit in source_units:
            unit_translation = translated_units.get(str(unit.get("id")))
            if unit_translation is None and len(source_units) == 1:
                unit_translation = translated
            unit_category, unit_category_reason = classify_dialogue(
                str(unit.get("decoded", "")), likelihood
            )
            unit_difficulty, unit_difficulty_reason = assess_display_difficulty(
                str(unit.get("decoded", "")), likelihood, [], kind="chr-record",
                source_offset=unit.get("source", {}).get("chrStart"),
            )
            message_units.append({
                "id": unit.get("id"),
                "ordinal": unit.get("ordinal"),
                "category": (
                    unit_translation.get("category", unit_category)
                    if unit_translation else unit_category
                ),
                "categoryEvidence": unit_category_reason,
                "sourceText": unit.get("decoded", ""),
                "translation": unit_translation.get("translation") if unit_translation else None,
                "translationStatus": (
                    unit_translation.get("translationStatus", "reviewed")
                    if unit_translation else "pending"
                ),
                "displayDifficulty": unit_difficulty,
                "displayDifficultyReason": unit_difficulty_reason,
                "source": unit.get("source"),
                "rawHex": unit.get("rawHex"),
                "separatorHex": unit.get("separatorHex"),
                "boundaryConfidence": unit.get("boundaryConfidence"),
            })
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
            "displayDifficulty": difficulty,
            "displayDifficultyReason": difficulty_reason,
            "staticLikelihood": likelihood,
            "unknownBytes": source.get("unknownBytes", []),
            "source": source.get("source"),
            "rawHex": source.get("rawHex"),
            "messageUnitCount": len(message_units),
            "messageUnits": message_units,
            "segmentation": source.get("segmentation"),
        })
    for source in dictionary.get("entries", []):
        translated = translations.get(str(source.get("id")))
        difficulty, difficulty_reason = assess_display_difficulty(
            str(source.get("normalized", source.get("decoded", ""))),
            "dictionary-entry", source.get("unknownBytes", []),
            kind="prg-dictionary-entry",
        )
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
            "displayDifficulty": difficulty,
            "displayDifficultyReason": difficulty_reason,
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
    difficulties = Counter(str(record["displayDifficulty"]) for record in records)
    chr_units = [
        unit for record in records if record["kind"] == "chr-record"
        for unit in record.get("messageUnits", [])
    ]
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
            "messageUnitCount": len(chr_units),
            "multiUnitContainerCount": sum(
                record.get("messageUnitCount", 0) > 1
                for record in records if record["kind"] == "chr-record"
            ),
            "messageUnitsByTranslationStatus": dict(sorted(Counter(
                unit["translationStatus"] for unit in chr_units
            ).items())),
            "byCategory": dict(sorted(counts.items())),
            "byTranslationStatus": dict(sorted(statuses.items())),
            "byDisplayDifficulty": dict(sorted(difficulties.items())),
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
        f"- CHR 消息单元：**{summary['messageUnitCount']}**（包含多个单元的 `$FC` 容器：{summary['multiUnitContainerCount']}）",
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
    lines.extend(["", "消息单元翻译状态：", ""])
    for status, count in summary["messageUnitsByTranslationStatus"].items():
        lines.append(f"- `{status}`：{count}")
    lines.extend(["", "## 游戏显示难度", ""])
    for difficulty, count in summary["byDisplayDifficulty"].items():
        lines.append(f"- `{difficulty}`：{count}")
    lines.extend([
        "",
        "`easy` 表示固定短文本、无动态变量和未解析字节；适合优先接入游戏。",
        "`medium` 通常只是较长或跨页；`hard` 则含动态对象、玩家名、数字或未解析编码。",
    ])
    easy_ready = [
        record for record in catalog["records"]
        if record["displayDifficulty"] == "easy"
        and record["translationStatus"] != "pending"
        and record["kind"] == "chr-record"
    ]
    lines.extend([
        "",
        f"## 建议优先接入游戏的固定文本（{len(easy_ready)} 条）",
        "",
        "这些记录已有中文，而且不依赖玩家名、敌人名、道具名或运行时数字。",
        "",
    ])
    for record in easy_ready:
        lines.append(f"- `{record['id']}`：{record['translation']}")
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
            f"### {record['id']} · `{record['category']}` · `{record['translationStatus']}` · display `{record['displayDifficulty']}`",
            "",
            f"- 位置：{location}",
            f"- 原文：{text}",
            f"- 中文：{translation}",
            f"- 显示判断：{record['displayDifficultyReason']}",
            "",
        ])
        if record.get("messageUnitCount", 1) > 1:
            lines.extend([
                f"- 注意：这是 `$FC` 容器概览；实际重新提取为 {record['messageUnitCount']} 个 `$FF` 分隔消息：",
                "",
            ])
            for unit in record["messageUnits"]:
                unit_source = unit.get("source") or {}
                unit_text = str(unit.get("sourceText", "")).rstrip().replace("\n", " / ")
                unit_translation = unit.get("translation") or "（待翻译/待确认）"
                lines.extend([
                    f"#### {unit['id']} · `{unit['translationStatus']}` · display `{unit['displayDifficulty']}`",
                    "",
                    f"- CHR：`${unit_source.get('chrStart', 0):04X}-${unit_source.get('chrEndExclusive', 0):04X}`",
                    f"- 原文：{unit_text}",
                    f"- 中文：{unit_translation}",
                    f"- 后置分隔字节：`{unit.get('separatorHex') or 'FC container end'}`",
                    f"- 边界置信度：`{unit.get('boundaryConfidence')}`",
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
