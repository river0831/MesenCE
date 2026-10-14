import unittest

from Tools.NesTranslation.bulk_text_catalog import (
    assess_display_difficulty,
    build_catalog,
    classify_dialogue,
)


class BulkTextCatalogTest(unittest.TestCase):
    def test_classifies_chest_and_battle_records(self) -> None:
        self.assertEqual(
            classify_dialogue("たからのはこが ある！", "high")[0],
            "chest-or-system",
        )
        self.assertEqual(
            classify_dialogue("スライムの こうげき！", "medium")[0], "battle"
        )

    def test_marks_fixed_text_easy_and_runtime_templates_hard(self) -> None:
        self.assertEqual(
            assess_display_difficulty(
                "ここには かいだんが ない<4F><END>", "high", [0x4F],
                kind="chr-record", source_offset=0x2140,
            )[0],
            "easy",
        )
        self.assertEqual(
            assess_display_difficulty(
                "{PLAYER_NAME}は <FD>を みつけた<END>", "high", [],
                kind="chr-record", source_offset=0x35E7,
            )[0],
            "hard",
        )
        self.assertEqual(
            assess_display_difficulty(
                "かなにみえるがタイルデータ<END>", "high", [],
                kind="chr-record", source_offset=0x5700,
            )[0],
            "hard",
        )

    def test_preserves_every_dialogue_and_dictionary_record(self) -> None:
        dialogue = {
            "romSha256": "abc",
            "records": [{
                "id": "chr-fc-1000",
                "decoded": "＊「こんにちは",
                "evidence": {"likelihood": "high"},
                "unknownBytes": [],
                "source": {"chrStart": 0x1000, "fileStart": 0x9000},
                "rawHex": "01 fc",
            }],
        }
        dictionary = {
            "entries": [{
                "id": "dict-a0",
                "normalized": "やくそう",
                "suggestedCategory": "item",
                "categoryEvidence": "known item",
                "unknownBytes": [],
                "prgStart": 1,
                "prgEndExclusive": 2,
                "token": 0xA0,
                "rawHex": "01",
            }],
        }
        translations = {
            "dict-a0": {"category": "item", "translation": "药草"},
        }
        result = build_catalog(dialogue, dictionary, translations)
        self.assertEqual(result["summary"]["recordCount"], 2)
        self.assertEqual(
            [record["id"] for record in result["records"]],
            ["chr-fc-1000", "dict-a0"],
        )
        self.assertEqual(result["records"][0]["translationStatus"], "pending")
        self.assertEqual(result["records"][1]["translation"], "药草")
        self.assertEqual(result["records"][1]["translationStatus"], "reviewed")

    def test_maps_split_unit_translations_without_using_container_summary(self) -> None:
        source = {
            "id": "chr-fc-22c4",
            "decoded": "first<FF>second<END>",
            "evidence": {"likelihood": "high"},
            "unknownBytes": [],
            "source": {"chrStart": 0x22C4, "fileStart": 0xA2D4},
            "rawHex": "01 ff 02 fc",
            "messageUnits": [
                {"id": "chr-fc-22c4-u1", "ordinal": 1,
                 "source": {"chrStart": 0x22C4, "chrEndExclusive": 0x22C5},
                 "decoded": "first", "rawHex": "01", "separatorHex": "ff",
                 "boundaryConfidence": "static-ff-boundary"},
                {"id": "chr-fc-22c4-u2", "ordinal": 2,
                 "source": {"chrStart": 0x22C6, "chrEndExclusive": 0x22C7},
                 "decoded": "second", "rawHex": "02", "separatorHex": "",
                 "boundaryConfidence": "container-terminator"},
            ],
        }
        translations = {
            "chr-fc-22c4": {
                "translation": "container only",
                "translationStatus": "container-summary",
                "units": [
                    {"id": "chr-fc-22c4-u1", "translation": "第一条",
                     "translationStatus": "draft"},
                    {"id": "chr-fc-22c4-u2", "translation": "第二条",
                     "translationStatus": "draft"},
                ],
            },
        }
        result = build_catalog(
            {"romSha256": "abc", "records": [source]},
            {"entries": []},
            translations,
        )
        units = result["records"][0]["messageUnits"]
        self.assertEqual([unit["translation"] for unit in units], ["第一条", "第二条"])
        self.assertEqual(result["summary"]["messageUnitCount"], 2)


if __name__ == "__main__":
    unittest.main()
