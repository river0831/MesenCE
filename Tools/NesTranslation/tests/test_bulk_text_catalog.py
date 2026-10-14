import unittest

from Tools.NesTranslation.bulk_text_catalog import build_catalog, classify_dialogue


class BulkTextCatalogTest(unittest.TestCase):
    def test_classifies_chest_and_battle_records(self) -> None:
        self.assertEqual(
            classify_dialogue("たからのはこが ある！", "high")[0],
            "chest-or-system",
        )
        self.assertEqual(
            classify_dialogue("スライムの こうげき！", "medium")[0], "battle"
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


if __name__ == "__main__":
    unittest.main()
