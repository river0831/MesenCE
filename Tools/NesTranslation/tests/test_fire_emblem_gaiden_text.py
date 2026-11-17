import unittest
from pathlib import Path

from Tools.NesTranslation.fire_emblem_gaiden_text import extract


class FireEmblemGaidenTextTest(unittest.TestCase):
    def test_extracts_controls_and_keeps_standalone_strings(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            (source / "bank001.asm").write_text(
                "L01B920:\n"
                ".STRINGMAP script_jp, \"アルム\"\n"
                "NEWLINE\n"
                ".STRINGMAP script_jp, \"ありがとう\"\n"
                "WAIT_CLICK\n"
                ".db STOP\n"
                "L01B940:\n"
                ".STRINGMAP script_jp, \"はい\"\n"
                ".db $00\n"
                "L01B950:\n"
                ".STRINGMAP script_jp, \"いいえ\"\n",
                encoding="utf-8",
            )

            segments, records = extract(source)

        self.assertEqual([item["text"] for item in segments], ["アルム", "ありがとう", "はい", "いいえ"])
        self.assertEqual(records[0]["text"], "アルム\nありがとう{wait}")
        self.assertTrue(records[0]["terminatedByStop"])
        self.assertEqual(records[1]["text"], "はい")
        self.assertEqual(records[2]["text"], "いいえ")


if __name__ == "__main__":
    unittest.main()
