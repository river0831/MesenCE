from __future__ import annotations

import json
import io
import tempfile
import unittest
from pathlib import Path

from Tools.NesTranslation.database import DatabaseError, load_database, validate_rom
from Tools.NesTranslation.dialogue_catalog import build_catalog, render_catalog_review
from Tools.NesTranslation.analyze_reads import cluster_reads
from Tools.NesTranslation.chr_records import ines_chr_layout, split_chr_records
from Tools.NesTranslation.catalog_validation import apply_runtime_matches
from Tools.NesTranslation.capture import build_capture_script
from Tools.NesTranslation.dictionary_codec import (
    expand_tokens,
    ines_prg,
    read_dictionary,
)
from Tools.NesTranslation.dictionary_catalog import (
    build_dictionary_catalog,
    normalize_japanese,
    validate_vocabulary,
    VocabularyError,
)
from Tools.NesTranslation.display import DebugRenderer
from Tools.NesTranslation.dialogue_overlay import (
    build_dialogue_overlay,
    load_mesen_font_characters,
    load_translation_spec,
    validate_presentation_characters,
)
from Tools.NesTranslation.dialogue_glyph_provenance import (
    build_script as build_glyph_provenance_script,
    group_visible_cells,
    logical_glyphs,
    select_segment,
    SubtitleEventRouter,
    validate_segments,
)
from Tools.NesTranslation.text_units import VisibilityUpdate, build_text_units
from Tools.NesTranslation.text_run_state import (
    NametableTextMatcher,
    NametableTextRunState,
    TextRun,
)
from Tools.NesTranslation.events import InputEvent, RomReadEvent
from Tools.NesTranslation.live import parse_trace_line, parse_trace_payload
from Tools.NesTranslation.message_instances import (
    GlyphComponent,
    InstanceState,
    MessageInstanceTracker,
)
from Tools.NesTranslation.overlay import build_overlay_script
from Tools.NesTranslation.provenance import build_provenance_script
from Tools.NesTranslation.replay import replay
from Tools.NesTranslation.review_worklist import (
    build_worklist as build_review_worklist,
    render_markdown as render_review_worklist,
)
from Tools.NesTranslation.resolver import TextResolver
from Tools.NesTranslation.runtime_catalog_match import (
    extract_runtime_bytes,
    match_catalog,
)
from Tools.NesTranslation.snapshot_replay import load_snapshots, replay_snapshots
from Tools.NesTranslation.snapshot_audit import audit_snapshots, render_markdown
from Tools.NesTranslation.text_review import load_character_map, render_bytes


ROOT = Path(__file__).parents[3]
DATABASE = ROOT / "Research/dragon-quest-jp/database/game-database.json"
ROM = ROOT / "test_roms/Dragon Quest (Japan).nes"
TRACE = ROOT / "Research/dragon-quest-jp/traces/main-menu-synthetic.jsonl"
CHARACTER_MAP = ROOT / "Research/dragon-quest-jp/database/character-map.json"
DIALOGUE_TRANSLATIONS = (
    ROOT / "Research/dragon-quest-jp/database/dialogue-translations.json"
)
VOCABULARY_TRANSLATIONS = (
    ROOT / "Research/dragon-quest-jp/database/vocabulary-translations.json"
)
SNAPSHOT_LIFECYCLE = (
    ROOT / "Tools/NesTranslation/tests/fixtures/visible-snapshot-lifecycle.jsonl"
)


def prg_byte(cpu_address: int) -> int:
    rom = ROM.read_bytes()
    return rom[16 + cpu_address - 0x8000]


def read_event(prg_offset: int, frame: int = 1) -> RomReadEvent:
    return RomReadEvent(
        type="rom-read",
        frame=frame,
        cpu_address=0x8000 + prg_offset,
        prg_offset=prg_offset,
        value=0,
        cpu_pc=0xC000,
    )


class DatabaseTests(unittest.TestCase):
    def test_message_instances_separate_repeated_record_lifecycles(self) -> None:
        tracker = MessageInstanceTracker()
        first = tracker.begin("dq.npc.king", frame=10)
        first.close(frame=20)
        second = tracker.begin("dq.npc.king", frame=100)
        self.assertEqual(first.record_id, second.record_id)
        self.assertNotEqual(first.id, second.id)
        self.assertEqual(first.state, InstanceState.CLOSED)
        self.assertEqual(second.state, InstanceState.ACTIVE)

    def test_message_instance_keeps_noncontiguous_source_trace(self) -> None:
        instance = MessageInstanceTracker().begin("shared-suffix", frame=1)
        for address in (0xA2C4, 0xA2C5, 0xB180, 0xB181):
            role = "template" if address < 0xB000 else "shared"
            instance.add_source_byte(address, bank=2, role=role)
        self.assertEqual(
            [(span.start, span.end_exclusive, span.role)
             for span in instance.source_spans],
            [(0xA2C4, 0xA2C6, "template"),
             (0xB180, 0xB182, "shared")],
        )

    def test_runtime_parameter_belongs_to_parent_message_instance(self) -> None:
        instance = MessageInstanceTracker().begin("found-item", frame=8)
        instance.ensure_parameter("ITEM", value_id=3)
        first = instance.add_character(
            "か", source_offset=None, source_type="parameter",
            parameter_slot="ITEM", frame=9,
        )
        second = instance.add_character(
            "ぎ", source_offset=None, source_type="parameter",
            parameter_slot="ITEM",
            components=(
                GlyphComponent(0x24, "base"),
                GlyphComponent(0xF8, "mark"),
            ), frame=9,
        )
        parameter = instance.parameters["ITEM"]
        self.assertEqual(parameter.value_id, 3)
        self.assertEqual(parameter.source_text, "かぎ")
        self.assertEqual(parameter.character_ids, [first.id, second.id])
        self.assertEqual(first.instance_id, instance.id)
        self.assertEqual(second.components[1].role, "mark")

    def test_closed_instance_rejects_more_runtime_output(self) -> None:
        instance = MessageInstanceTracker().begin("dialogue", frame=1)
        instance.close(frame=2)
        with self.assertRaisesRegex(ValueError, "already closed"):
            instance.add_character("あ", source_offset=0)

    def test_capture_script_can_start_immediately_with_longer_limit(self) -> None:
        script = build_capture_script(
            "print('trace')", start_immediately=True, frame_limit=18000
        )
        self.assertTrue(script.startswith("DQ_CAPTURE_IMMEDIATELY = true\n"))
        self.assertIn("DQ_CAPTURE_FRAME_LIMIT = 18000", script)
        with self.assertRaisesRegex(ValueError, "positive"):
            build_capture_script("", start_immediately=False, frame_limit=0)

    def test_database_matches_exact_rom_bytes(self) -> None:
        database = load_database(DATABASE)
        validate_rom(database, ROM)
        self.assertEqual(database.records[0].raw_bytes[0], 0x3C)
        self.assertEqual(database.records[0].raw_bytes[-1], 0xFF)
        self.assertEqual(database.records[0].dismiss_input_mask, 0x02)
        self.assertEqual(
            database.records[0].deactivation_confidence,
            "runtime-confirmed",
        )
        strength = database.records[1]
        self.assertEqual(strength.id, "dq.menu.strength")
        self.assertEqual(strength.prg_start, 0x030F)
        self.assertEqual(strength.prg_end_exclusive, 0x03F6)
        self.assertIsNone(strength.return_to_record_id)
        self.assertEqual(len(database.records[0].presentation.labels), 8)
        self.assertEqual(
            database.records[0].presentation.labels[0].source_start, 2
        )
        self.assertEqual(
            database.records[0].presentation.labels[0].source_end_exclusive, 5
        )
        self.assertEqual(len(strength.presentation.labels), 10)
        assert database.ppu_update_buffer is not None
        self.assertEqual(database.ppu_update_buffer.ram_start, 0x0300)
        self.assertEqual(database.ppu_update_buffer.ram_end_exclusive, 0x03C0)
        self.assertEqual(database.ppu_update_buffer.entry_size, 3)
        self.assertEqual(database.ppu_update_buffer.value_offset, 2)
        self.assertEqual(database.ppu_update_buffer.writer_pc, 0xABBB)
        self.assertEqual(database.ppu_update_buffer.confidence, "code-confirmed")

    def test_wrong_rom_hash_is_rejected(self) -> None:
        database = load_database(DATABASE)
        with tempfile.TemporaryDirectory() as folder:
            fake_rom = Path(folder) / "fake.nes"
            fake_rom.write_bytes(b"NES\x1a" + bytes(32))
            with self.assertRaisesRegex(DatabaseError, "SHA-256 mismatch"):
                validate_rom(database, fake_rom)

    def test_duplicate_record_ids_are_rejected(self) -> None:
        value = json.loads(DATABASE.read_text(encoding="utf-8"))
        value["records"].append(dict(value["records"][0]))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "database.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(DatabaseError, "duplicate record id"):
                load_database(path)

    def test_invalid_presentation_dimensions_are_rejected(self) -> None:
        value = json.loads(DATABASE.read_text(encoding="utf-8"))
        value["records"][0]["presentation"]["labels"][0]["clear"]["width"] = 0
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "database.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(DatabaseError, "dimensions must be positive"):
                load_database(path)

    def test_invalid_ppu_buffer_offset_is_rejected(self) -> None:
        value = json.loads(DATABASE.read_text(encoding="utf-8"))
        value["runtime"]["ppuUpdateBuffer"]["valueOffset"] = 3
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "database.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(DatabaseError, "offsets must fit"):
                load_database(path)

    def test_invalid_ppu_buffer_writer_pc_is_rejected(self) -> None:
        value = json.loads(DATABASE.read_text(encoding="utf-8"))
        value["runtime"]["ppuUpdateBuffer"]["writerPc"] = 0x10000
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "database.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(DatabaseError, "writerPc must fit"):
                load_database(path)

    def test_overlay_script_is_generated_from_database(self) -> None:
        database = load_database(DATABASE)
        template_path = (
            ROOT / "Research/dragon-quest-jp/runtime/database-overlay.lua"
        )
        script = build_overlay_script(
            database,
            template_path.read_text(encoding="utf-8"),
        )
        self.assertNotIn("__NES_TRANSLATION_CONFIG__", script)
        self.assertIn('id = "dq.menu.main"', script)
        self.assertIn('id = "dq.menu.strength"', script)
        self.assertIn('text = "等級:"', script)
        self.assertIn("startAddress = 33881", script)
        self.assertIn("local inputAddress = 71", script)

    def test_provenance_script_is_generated_from_database(self) -> None:
        database = load_database(DATABASE)
        template = (
            ROOT / "Research/dragon-quest-jp/runtime/nametable-provenance.lua"
        ).read_text(encoding="utf-8")
        script = build_provenance_script(database, template, source_ttl_frames=4)
        self.assertNotIn("__NES_TRANSLATION_PROVENANCE_CONFIG__", script)
        self.assertIn("local sourceTtlFrames = 4", script)
        self.assertIn('id = "dq.menu.main"', script)
        self.assertIn("startAddress = 33881", script)
        self.assertIn("endAddress = 33946", script)
        self.assertIn("ramStart = 768", script)
        self.assertIn("valueOffset = 2", script)
        self.assertIn("writerPc = 43963", script)

    def test_provenance_rejects_negative_ttl(self) -> None:
        database = load_database(DATABASE)
        with self.assertRaisesRegex(ValueError, "non-negative"):
            build_provenance_script(
                database, "-- __NES_TRANSLATION_PROVENANCE_CONFIG__", -1
            )

    def test_buffer_provenance_template_uses_same_database_contract(self) -> None:
        database = load_database(DATABASE)
        template = (
            ROOT / "Research/dragon-quest-jp/runtime/ppu-buffer-provenance.lua"
        ).read_text(encoding="utf-8")
        script = build_provenance_script(database, template)
        self.assertNotIn("__NES_TRANSLATION_PROVENANCE_CONFIG__", script)
        self.assertIn('id = "dq.menu.main"', script)
        self.assertIn('id = "dq.menu.strength"', script)
        self.assertIn("emu.memType.nesNametableRam", script)

    def test_provenance_overlay_contains_database_labels(self) -> None:
        database = load_database(DATABASE)
        template = (
            ROOT / "Research/dragon-quest-jp/runtime/provenance-overlay.lua"
        ).read_text(encoding="utf-8")
        script = build_provenance_script(database, template)
        self.assertNotIn("__NES_TRANSLATION_PROVENANCE_CONFIG__", script)
        self.assertIn('text = "等級:"', script)
        self.assertIn("clearWidth = 78", script)
        self.assertIn("restoreRatio = 0.80", script)
        self.assertIn("bulkClearThreshold = 8", script)
        self.assertIn("clearWidth = 58", script)

    def test_dialogue_overlay_uses_confirmed_catalog_bytes_and_translation(self) -> None:
        spec = load_translation_spec(DIALOGUE_TRANSLATIONS)
        catalog = {
            "records": [
                {
                    "id": item["id"],
                    "rawHex": (
                        ("55 62 fc", "6d fe fc", "70 fd fc")[index]
                        if index < 3 else f"{0x80 + index:02x} fc"
                    ),
                    "runtime": {"status": "runtime-confirmed"},
                }
                for index, item in enumerate(spec["records"])
            ]
        }
        template = (
            ROOT / "Research/dragon-quest-jp/runtime/dialogue-overlay.lua"
        ).read_text(encoding="utf-8")
        script = build_dialogue_overlay(catalog, spec, template)
        self.assertNotIn("__NES_TRANSLATION_DIALOGUE_CONFIG__", script)
        self.assertIn('id = "chr-fc-35c8"', script)
        self.assertIn("matchPrefix = { 85, 98, 252 }", script)
        self.assertIn("這裡什麼也拿不到。", script)
        self.assertIn("離開城堡後，旁邊有座城鎮。", script)
        self.assertIn("local visibilityStart = 576", script)
        self.assertIn("and not activeIsVisible", script)
        self.assertIn("frame - lastVisibilityWriteFrame >= stableRegionFrames", script)

    def test_dialogue_overlay_rejects_unverified_catalog_record(self) -> None:
        spec = load_translation_spec(DIALOGUE_TRANSLATIONS)
        catalog = {
            "records": [
                {
                    "id": item["id"],
                    "rawHex": "fc",
                    "runtime": {"status": "unverified"},
                }
                for item in spec["records"]
            ]
        }
        with self.assertRaisesRegex(DatabaseError, "not runtime-confirmed"):
            build_dialogue_overlay(catalog, spec, "-- __NES_TRANSLATION_DIALOGUE_CONFIG__")

    def test_dialogue_presentation_uses_only_mesen_hud_glyphs(self) -> None:
        spec = load_translation_spec(DIALOGUE_TRANSLATIONS)
        supported = load_mesen_font_characters(
            ROOT / "Core/Shared/Video/DrawStringCommand.cpp"
        )
        validate_presentation_characters(spec, supported)
        broken = json.loads(json.dumps(spec, ensure_ascii=False))
        broken["records"][0]["pages"][0]["lines"] = ["这里什么也拿不到。"]
        with self.assertRaisesRegex(DatabaseError, "么这"):
            validate_presentation_characters(broken, supported)

        segment_broken = json.loads(json.dumps(spec, ensure_ascii=False))
        segment_broken["records"][0]["segments"] = [{"lines": ["这"]}]
        with self.assertRaisesRegex(DatabaseError, "这"):
            validate_presentation_characters(segment_broken, supported)

    def test_opening_speech_has_complete_reviewed_segments(self) -> None:
        spec = json.loads(DIALOGUE_TRANSLATIONS.read_text(encoding="utf-8"))
        opening = next(
            record for record in spec["records"] if record["id"] == "chr-fc-3908"
        )
        validate_segments(opening, 278)
        self.assertEqual(len(opening["segments"]), 8)
        self.assertEqual(opening["segments"][0]["sourceStart"], 0)
        self.assertEqual(opening["segments"][-1]["sourceEndExclusive"], 278)

    def test_opening_room_dialogues_have_complete_reviewed_segments(self) -> None:
        spec = json.loads(DIALOGUE_TRANSLATIONS.read_text(encoding="utf-8"))
        expected_counts = {
            "chr-fc-3847": 90,
            "chr-fc-3002": 14,
            "chr-fc-35e7": 7,
            "chr-fc-3397": 39,
            "chr-fc-215b": 16,
        }
        records = {record["id"]: record for record in spec["records"]}
        for record_id, glyph_count in expected_counts.items():
            with self.subTest(record_id=record_id):
                validate_segments(records[record_id], glyph_count)


class ReviewWorklistTests(unittest.TestCase):
    def test_worklist_preserves_and_prioritizes_every_catalog_record(self) -> None:
        catalog = {
            "romSha256": "a" * 64,
            "records": [
                {
                    "id": "translated", "decoded": "＊「こんにちは", "unknownBytes": [],
                    "metrics": {"score": 0.9, "glyphCount": 6},
                    "evidence": {"likelihood": "high"},
                    "runtime": {"status": "runtime-confirmed"},
                    "source": {"chrStart": 1, "chrEndExclusive": 8},
                },
                {
                    "id": "item-result", "decoded": "かぎを みつけた", "unknownBytes": [0xFD],
                    "metrics": {"score": 0.8, "glyphCount": 8},
                    "evidence": {"likelihood": "medium"},
                    "runtime": {"status": "runtime-confirmed"},
                    "source": {"chrStart": 9, "chrEndExclusive": 18},
                },
                {
                    "id": "low", "decoded": "<00>", "unknownBytes": [0],
                    "metrics": {"score": 0.1, "glyphCount": 0},
                    "evidence": {"likelihood": "low"},
                    "runtime": {"status": "unverified"},
                    "source": {"chrStart": 19, "chrEndExclusive": 20},
                },
            ],
        }
        worklist = build_review_worklist(
            catalog, {"records": [{"id": "translated"}]}
        )
        self.assertEqual(len(worklist["records"]), 3)
        self.assertEqual([item["id"] for item in worklist["records"]], [
            "translated", "item-result", "low",
        ])
        self.assertEqual(worklist["records"][1]["suggestedCategory"], "system-or-template")
        self.assertEqual(worklist["summary"]["runtimeConfirmedPending"], 1)
        self.assertTrue(worklist["policy"]["preservesAllCatalogRecords"])

    def test_markdown_omits_low_priority_body_but_reports_lossless_json(self) -> None:
        worklist = {
            "romSha256": "b" * 64,
            "summary": {
                "recordCount": 1, "translated": 0, "pending": 1,
                "runtimeConfirmedPending": 0,
                "bySuggestedCategory": {"unclassified": 1},
            },
            "records": [{
                "id": "low", "priority": 4, "priorityReason": "low static likelihood",
                "suggestedCategory": "unclassified", "runtimeStatus": "unverified",
                "staticLikelihood": "low", "score": 0.1, "unknownBytes": [],
                "source": {"chrStart": 0, "chrEndExclusive": 1}, "decoded": "noise",
            }],
        }
        rendered = render_review_worklist(worklist)
        self.assertIn("Catalog records preserved: 1", rendered)
        self.assertNotIn("### low", rendered)


class DictionaryCatalogTests(unittest.TestCase):
    def test_dictionary_catalog_preserves_offsets_and_empty_entries(self) -> None:
        rom = bytearray(16 + 0x4000 + 0x2000)
        rom[:4] = b"NES\x1a"
        rom[4] = 1
        rom[5] = 1
        rom[16:21] = bytes([0x0F, 0xF8, 0xFA, 0xFA, 0x0B])
        rom[21] = 0xFA
        character_map = {
            0x0F: {"display": "か", "type": "glyph"},
            0x0B: {"display": "い", "type": "glyph"},
            0xF8: {"display": "゛", "type": "modifier"},
        }
        catalog = build_dictionary_catalog(
            bytes(rom), start=0, end_exclusive=6, terminator=0xFA,
            token_base=0x6D, character_map=character_map,
        )
        self.assertEqual([item["id"] for item in catalog["entries"]], [
            "dict-6d", "dict-6e", "dict-6f",
        ])
        self.assertEqual(catalog["entries"][0]["normalized"], "が")
        self.assertEqual(catalog["entries"][1]["rawHex"], "")
        self.assertEqual(catalog["entries"][2]["prgStart"], 4)

    def test_japanese_modifier_normalization(self) -> None:
        self.assertEqual(normalize_japanese("か゛き゛"), "がぎ")

    def test_vocabulary_must_reference_matching_dictionary_token(self) -> None:
        catalog = {"entries": [{
            "id": "dict-a1", "token": 0xA1, "normalized": "かぎ", "unknownBytes": [],
        }]}
        vocabulary = {"records": [{
            "id": "dict-a1", "token": 0xA1, "category": "item",
            "sourceText": "かぎ", "translation": "钥匙", "display": "鑰匙",
            "confidence": "semantic-probable",
        }]}
        validate_vocabulary(catalog, vocabulary)
        vocabulary["records"][0]["token"] = 0xA2
        with self.assertRaisesRegex(VocabularyError, "source mismatch"):
            validate_vocabulary(catalog, vocabulary)


class ReadAnalysisTests(unittest.TestCase):
    def test_incremental_text_runs_update_only_touched_rows(self) -> None:
        state = NametableTextRunState()
        changed = state.apply({
            "type": "writes",
            "frame": 10,
            "runs": [
                {"row": 20, "startColumn": 4, "hex": "0f10"},
                {"row": 22, "startColumn": 7, "hex": "291b"},
            ],
        })
        self.assertEqual(changed, (20, 22))
        self.assertEqual(state.known_runs(20), (TextRun(20, 4, (0x0F, 0x10)),))
        state.apply({
            "type": "writes", "frame": 11,
            "runs": [{"row": 20, "startColumn": 6, "hex": "1219"}],
        })
        self.assertEqual(
            state.known_runs(20),
            (TextRun(20, 4, (0x0F, 0x10, 0x12, 0x19)),),
        )

    def test_incremental_text_runs_reject_out_of_bounds_updates(self) -> None:
        state = NametableTextRunState()
        with self.assertRaisesRegex(ValueError, "exceeds"):
            state.apply({
                "type": "writes",
                "runs": [{"row": 20, "startColumn": 31, "hex": "0f10"}],
            })

    def test_incremental_matcher_reconstructs_captured_gold_message(self) -> None:
        vocabulary = json.loads(VOCABULARY_TRANSLATIONS.read_text(encoding="utf-8"))
        catalog = json.loads((
            ROOT / "Research/dragon-quest-jp/generated/prg-dictionary-catalog.json"
        ).read_text(encoding="utf-8"))
        matcher = NametableTextMatcher(vocabulary, catalog)
        events = [
            {"type": "writes", "runs": [{
                "row": 20, "startColumn": 15, "hex": "010200454e4342",
            }]},
            {"type": "writes", "runs": [{
                "row": 22, "startColumn": 9, "hex": "1c1f0b3319",
            }]},
        ]
        self.assertIsNone(matcher.apply(events[0]))
        match = matcher.apply(events[1])
        assert match is not None
        self.assertEqual(match.text, "獲得了120金幣。")
        self.assertEqual((match.left, match.top, match.right, match.bottom), (
            9, 20, 22, 23,
        ))

    def test_incremental_matcher_waits_for_complete_item_action(self) -> None:
        vocabulary = json.loads(VOCABULARY_TRANSLATIONS.read_text(encoding="utf-8"))
        catalog = json.loads((
            ROOT / "Research/dragon-quest-jp/generated/prg-dictionary-catalog.json"
        ).read_text(encoding="utf-8"))
        matcher = NametableTextMatcher(vocabulary, catalog)
        self.assertIsNone(matcher.apply({
            "type": "writes",
            "runs": [{"row": 20, "startColumn": 17, "hex": "190b281b"}],
        }))
        self.assertIsNone(matcher.apply({
            "type": "writes",
            "runs": [{"row": 22, "startColumn": 11, "hex": "291b12"}],
        }))
        match = matcher.apply({
            "type": "writes",
            "runs": [{"row": 22, "startColumn": 14, "hex": "19"}],
        })
        assert match is not None
        self.assertEqual(match.text, "發現了火把。")

    def test_incremental_matcher_allows_reviewed_voicing_tile_variation(self) -> None:
        vocabulary = json.loads(VOCABULARY_TRANSLATIONS.read_text(encoding="utf-8"))
        catalog = json.loads((
            ROOT / "Research/dragon-quest-jp/generated/prg-dictionary-catalog.json"
        ).read_text(encoding="utf-8"))
        matcher = NametableTextMatcher(vocabulary, catalog)
        # かぎ is encoded as 0f 10 f8 in source. The modifier marks only the
        # second visible glyph as variable when the PPU uses a composed tile.
        self.assertIsNone(matcher.apply({
            "type": "writes",
            "runs": [{"row": 20, "startColumn": 17, "hex": "0f9936"}],
        }))
        match = matcher.apply({
            "type": "writes",
            "runs": [{"row": 22, "startColumn": 11, "hex": "291b1219"}],
        })
        assert match is not None
        self.assertEqual(match.text, "發現了鑰匙。")

    def test_incremental_matcher_does_not_fuzz_unmodified_glyphs(self) -> None:
        vocabulary = json.loads(VOCABULARY_TRANSLATIONS.read_text(encoding="utf-8"))
        catalog = json.loads((
            ROOT / "Research/dragon-quest-jp/generated/prg-dictionary-catalog.json"
        ).read_text(encoding="utf-8"))
        matcher = NametableTextMatcher(vocabulary, catalog)
        matcher.apply({
            "type": "writes",
            "runs": [{"row": 20, "startColumn": 17, "hex": "990b281b"}],
        })
        match = matcher.apply({
            "type": "writes",
            "runs": [{"row": 22, "startColumn": 11, "hex": "291b1219"}],
        })
        self.assertIsNone(match)

    def test_router_projects_and_clears_incremental_message(self) -> None:
        vocabulary = json.loads(VOCABULARY_TRANSLATIONS.read_text(encoding="utf-8"))
        catalog = json.loads((
            ROOT / "Research/dragon-quest-jp/generated/prg-dictionary-catalog.json"
        ).read_text(encoding="utf-8"))
        router = SubtitleEventRouter(
            json.loads(DIALOGUE_TRANSLATIONS.read_text(encoding="utf-8")),
            load_database(DATABASE), vocabulary, dictionary_catalog=catalog,
        )
        self.assertIsNone(router.consume(
            'DQRUN {"type":"writes","frame":1,"runs":['
            '{"row":20,"startColumn":17,"hex":"190b281b"}]}'
        ))
        shown = router.consume(
            'DQRUN {"type":"writes","frame":2,"runs":['
            '{"row":22,"startColumn":11,"hex":"291b1219"}]}'
        )
        assert shown is not None
        self.assertEqual([item["text"] for item in shown["items"]], [
            "發現了火把。"
        ])
        self.assertEqual(shown["items"][0]["ppuBounds"], {
            "x": 88, "y": 160, "width": 80, "height": 24,
        })
        cleared = router.consume(
            'DQRUN {"type":"writes","frame":3,"runs":['
            '{"row":20,"startColumn":17,"hex":"5f5f5f5f"},'
            '{"row":22,"startColumn":11,"hex":"5f5f5f5f"}]}'
        )
        assert cleared is not None
        self.assertFalse(cleared["visible"])

    def test_logical_glyphs_skip_controls_and_collapse_modifier(self) -> None:
        character_map = load_character_map(CHARACTER_MAP)
        record = {
            "tokens": [
                {"source_offset": 10, "expanded": [0x24, 0xF8]},
                {"source_offset": 11, "expanded": [0xFE]},
                {"source_offset": 12, "expanded": [0x19]},
            ]
        }
        glyphs = logical_glyphs(record, character_map)
        self.assertEqual([glyph.value for glyph in glyphs], [0x24, 0x19])
        self.assertEqual([glyph.index for glyph in glyphs], [0, 1])
        self.assertEqual(glyphs[0].source_offset, 10)
        self.assertEqual(glyphs[1].expanded_index, 3)

    def test_visible_cells_group_into_source_ranges(self) -> None:
        rows = group_visible_cells([
            (0x287, "record-a", 20),
            (0x288, "record-a", 21),
            (0x2A7, "record-a", 30),
        ])
        self.assertEqual(rows[0]["row"], 20)
        self.assertEqual(rows[0]["start"], 20)
        self.assertEqual(rows[0]["endExclusive"], 22)
        self.assertEqual(rows[1]["start"], 30)

    def test_segment_selection_uses_newest_visible_glyph(self) -> None:
        segments = [
            {"sourceStart": 0, "sourceEndExclusive": 46, "lines": ["one"]},
            {"sourceStart": 46, "sourceEndExclusive": 64, "lines": ["two"]},
        ]
        self.assertEqual(select_segment(segments, [37, 45]), 0)
        self.assertEqual(select_segment(segments, [37, 46]), 1)
        self.assertIsNone(select_segment(segments, []))

    def test_segments_must_cover_logical_glyphs_without_gaps(self) -> None:
        valid = {"id": "sample", "segments": [
            {"sourceStart": 0, "sourceEndExclusive": 2, "lines": ["one"]},
            {"sourceStart": 2, "sourceEndExclusive": 4, "lines": ["two"]},
        ]}
        validate_segments(valid, 4)
        broken = json.loads(json.dumps(valid))
        broken["segments"][1]["sourceStart"] = 3
        with self.assertRaisesRegex(DatabaseError, "contiguous"):
            validate_segments(broken, 4)

    def test_subtitle_router_maps_segment_and_reset_events(self) -> None:
        spec = json.loads(DIALOGUE_TRANSLATIONS.read_text(encoding="utf-8"))
        router = SubtitleEventRouter(spec, load_database(DATABASE))
        partial = router.consume(
            'DQGLYPH {"type":"coverage","recordId":"chr-fc-38a7",'
            '"segments":[{"sourceStart":0,"sourceEndExclusive":22,'
            '"visibleCount":4}]}'
        )
        assert partial is not None
        self.assertFalse(partial["visible"])
        shown = router.consume(
            'DQGLYPH {"type":"coverage","recordId":"chr-fc-38a7",'
            '"segments":[{"sourceStart":0,"sourceEndExclusive":22,'
            '"visibleCount":18},{"sourceStart":22,"sourceEndExclusive":46,'
            '"visibleCount":0}]}'
        )
        assert shown is not None
        self.assertTrue(shown["visible"])
        self.assertEqual([item["text"] for item in shown["items"]], [
            "離開城堡後，旁邊有座城鎮。"
        ])
        both = router.consume(
            'DQGLYPH {"type":"coverage","recordId":"chr-fc-38a7",'
            '"segments":[{"sourceStart":0,"sourceEndExclusive":22,'
            '"visibleCount":22},{"sourceStart":22,"sourceEndExclusive":46,'
            '"visibleCount":20}]}'
        )
        assert both is not None
        self.assertIn("先在那裡備齊武器和防具。", [
            item["text"] for item in both["items"]
        ])
        cleared = router.consume(
            'DQGLYPH {"type":"coverage","recordId":"chr-fc-38a7",'
            '"segments":[{"sourceStart":0,"sourceEndExclusive":22,'
            '"visibleCount":0},{"sourceStart":22,"sourceEndExclusive":46,'
            '"visibleCount":0}]}'
        )
        assert cleared is not None
        self.assertFalse(cleared["visible"])
        replacement = router.consume(
            'DQGLYPH {"type":"coverage","recordId":"chr-fc-38a7",'
            '"segments":[{"sourceStart":46,"sourceEndExclusive":64,'
            '"visibleCount":15}]}'
        )
        assert replacement is not None
        self.assertEqual([item["text"] for item in replacement["items"]], [
            "戰鬥中受傷時，"
        ])
        hidden = router.consume(
            'DQGLYPH {"type":"reset","recordId":"chr-fc-38a7"}'
        )
        assert hidden is not None
        self.assertFalse(hidden["visible"])
        self.assertIsNone(router.consume("ordinary emulator output"))

    def test_text_units_normalize_layout_and_dialogue_sources(self) -> None:
        spec = json.loads(DIALOGUE_TRANSLATIONS.read_text(encoding="utf-8"))
        units = build_text_units(spec, load_database(DATABASE))
        by_id = {unit.id: unit for unit in units}

        menu = by_id["dq.menu.main#label-4"]
        self.assertEqual(menu.text, "道具")
        self.assertEqual(menu.ppu_bounds.as_dict(), {
            "x": 174, "y": 48, "width": 40, "height": 12,
        })
        self.assertEqual(menu.total_count, 10)
        self.assertEqual(menu.kind, "label")
        self.assertEqual(menu.source_index, 4)
        self.assertIsNone(menu.source_start)

        dialogue = by_id["chr-fc-38a7#glyph-0-22"]
        self.assertEqual(dialogue.text, "離開城堡後，旁邊有座城鎮。")
        self.assertEqual(dialogue.total_count, 22)
        self.assertEqual(dialogue.kind, "dialogue")
        self.assertEqual(dialogue.source_start, 0)
        self.assertEqual(dialogue.source_end_exclusive, 22)
        self.assertEqual(dialogue.line_height, 15)

    def test_router_accepts_generic_visibility_updates(self) -> None:
        router = SubtitleEventRouter(
            json.loads(DIALOGUE_TRANSLATIONS.read_text(encoding="utf-8")),
            load_database(DATABASE),
        )
        shown = router.apply_visibility(VisibilityUpdate(
            "label:dq.menu.main", (("dq.menu.main#label-4", 10),)
        ))
        self.assertEqual([item["text"] for item in shown["items"]], ["道具"])
        hidden = router.apply_visibility(VisibilityUpdate(
            "label:dq.menu.main", ()
        ))
        self.assertFalse(hidden["visible"])
        with self.assertRaisesRegex(ValueError, "outside scope"):
            router.apply_visibility(VisibilityUpdate(
                "label:dq.menu.main", (("dq.menu.strength#label-1", 1),)
            ))

    def test_vocabulary_visibility_uses_runtime_ppu_bounds(self) -> None:
        vocabulary = json.loads(VOCABULARY_TRANSLATIONS.read_text(encoding="utf-8"))
        router = SubtitleEventRouter(
            json.loads(DIALOGUE_TRANSLATIONS.read_text(encoding="utf-8")),
            load_database(DATABASE), vocabulary,
        )
        shown = router.consume(
            'DQMENU {"type":"group","frame":9,"recordId":"dict-a1",'
            '"cellCount":3,"labels":[{"index":1,"cellCount":3,'
            '"x":168,"y":64,"width":24,"height":8}]}'
        )
        assert shown is not None
        self.assertEqual(shown["items"][0]["text"], "鑰匙")
        self.assertEqual(shown["items"][0]["ppuBounds"], {
            "x": 168, "y": 64, "width": 24, "height": 8,
        })
        dialogue = router.apply_visibility(VisibilityUpdate(
            "dialogue:chr-fc-35e7", (("chr-fc-35e7#glyph-0-7", 7),)
        ))
        self.assertEqual([item["text"] for item in dialogue["items"]], [
            "發現了物品。"
        ])
        restored = router.apply_visibility(VisibilityUpdate(
            "dialogue:chr-fc-35e7", ()
        ))
        self.assertEqual([item["text"] for item in restored["items"]], ["鑰匙"])
        hidden = router.consume(
            'DQMENU {"type":"group","frame":10,"recordId":"dict-a1",'
            '"cellCount":0,"labels":[]}'
        )
        assert hidden is not None
        self.assertFalse(hidden["visible"])

    def test_system_template_fragments_are_not_independent_text_units(self) -> None:
        vocabulary = json.loads(VOCABULARY_TRANSLATIONS.read_text(encoding="utf-8"))
        units = build_text_units({}, vocabulary=vocabulary)
        ids = {unit.id for unit in units}
        self.assertIn("dict-a1#vocabulary", ids)
        self.assertNotIn("dict-ba#vocabulary", ids)
        self.assertNotIn("dict-bb#vocabulary", ids)

    def test_subtitle_router_maps_menu_groups_to_layout_labels(self) -> None:
        router = SubtitleEventRouter(
            json.loads(DIALOGUE_TRANSLATIONS.read_text(encoding="utf-8")),
            load_database(DATABASE),
        )
        shown = router.consume(
            'DQMENU {"type":"group","recordId":"dq.menu.main","cellCount":113}'
        )
        assert shown is not None
        self.assertEqual(shown["mode"], "visible-translation-snapshot")
        self.assertEqual(len(shown["items"]), 8)
        self.assertEqual(shown["items"][3]["text"], "道具")
        self.assertEqual(
            shown["items"][3]["ppuBounds"],
            {"x": 174, "y": 48, "width": 40, "height": 12},
        )
        self.assertEqual(shown["items"][3]["unitId"], "dq.menu.main#label-4")
        self.assertEqual(shown["items"][3]["visibleRatio"], 1.0)
        hidden = router.consume(
            'DQMENU {"type":"group","recordId":"dq.menu.main","cellCount":0}'
        )
        assert hidden is not None
        self.assertFalse(hidden["visible"])

    def test_subtitle_router_filters_individual_visible_menu_labels(self) -> None:
        router = SubtitleEventRouter(
            json.loads(DIALOGUE_TRANSLATIONS.read_text(encoding="utf-8")),
            load_database(DATABASE),
        )
        scene = router.consume(
            'DQMENU {"type":"group","recordId":"dq.menu.main",'
            '"cellCount":12,"labels":[{"index":1,"cellCount":6},'
            '{"index":2,"cellCount":6}]}'
        )
        assert scene is not None
        self.assertEqual(
            [item["text"] for item in scene["items"]], ["交談", "咒文"]
        )
        self.assertEqual(scene["delta"], {
            "appeared": ["dq.menu.main#label-1", "dq.menu.main#label-2"],
            "updated": [],
            "disappeared": [],
        })
        changed = router.consume(
            'DQMENU {"type":"group","recordId":"dq.menu.main",'
            '"cellCount":11,"labels":[{"index":1,"cellCount":5},'
            '{"index":2,"cellCount":6}]}'
        )
        assert changed is not None
        self.assertEqual(changed["delta"], {
            "appeared": [],
            "updated": ["dq.menu.main#label-1"],
            "disappeared": [],
        })
        removed = router.consume(
            'DQMENU {"type":"group","recordId":"dq.menu.main",'
            '"cellCount":6,"labels":[{"index":2,"cellCount":6}]}'
        )
        assert removed is not None
        self.assertEqual(removed["delta"], {
            "appeared": [],
            "updated": [],
            "disappeared": ["dq.menu.main#label-1"],
        })

    def test_subtitle_router_composes_menu_and_dialogue_from_current_state(self) -> None:
        router = SubtitleEventRouter(
            json.loads(DIALOGUE_TRANSLATIONS.read_text(encoding="utf-8")),
            load_database(DATABASE),
        )
        router.consume(
            'DQMENU {"type":"group","recordId":"dq.menu.main","cellCount":113}'
        )
        scene = router.consume(
            'DQGLYPH {"type":"coverage","recordId":"chr-fc-38a7",'
            '"segments":[{"sourceStart":0,"sourceEndExclusive":22,'
            '"visibleCount":6},{"sourceStart":22,"sourceEndExclusive":46,'
            '"visibleCount":0}]}'
        )
        assert scene is not None
        self.assertEqual(len(scene["items"]), 9)
        self.assertEqual(scene["items"][-1]["text"], "離開城堡後，旁邊有座城鎮。")
        self.assertEqual(
            scene["items"][-1]["ppuBounds"],
            {"x": 52, "y": 175, "width": 152, "height": 15},
        )
        self.assertEqual(scene["items"][-1]["visibleCount"], 6)
        self.assertEqual(scene["items"][-1]["totalCount"], 22)
        scene = router.consume(
            'DQGLYPH {"type":"coverage","recordId":"chr-fc-38a7",'
            '"segments":[{"sourceStart":0,"sourceEndExclusive":22,'
            '"visibleCount":0},{"sourceStart":22,"sourceEndExclusive":46,'
            '"visibleCount":6}]}'
        )
        assert scene is not None
        self.assertEqual(scene["items"][-1]["text"], "先在那裡備齊武器和防具。")
        reset = router.consume(
            'DQGLYPH {"type":"reset","recordId":"chr-fc-38a7"}'
        )
        assert reset is not None
        self.assertTrue(reset["visible"])
        self.assertEqual(len(reset["items"]), 8)
        self.assertTrue(all("#label-" in item["unitId"] for item in reset["items"]))

    def test_source_record_fallback_shows_variable_chest_message(self) -> None:
        vocabulary = json.loads(VOCABULARY_TRANSLATIONS.read_text(encoding="utf-8"))
        catalog = json.loads((
            ROOT / "Research/dragon-quest-jp/generated/prg-dictionary-catalog.json"
        ).read_text(encoding="utf-8"))
        router = SubtitleEventRouter(
            json.loads(DIALOGUE_TRANSLATIONS.read_text(encoding="utf-8")),
            load_database(DATABASE), vocabulary, catalog,
        )
        self.assertIsNone(router.consume(
            'DQTERM {"type":"source-term","frame":8,"recordId":"dict-a0"}'
        ))
        self.assertIsNone(router.consume(
            'DQTERM {"type":"source-term","frame":8,"recordId":"dict-a1"}'
        ))
        # A later dictionary scan for the action passes another item. It must
        # not replace the object selected by the earlier scan.
        self.assertIsNone(router.consume(
            'DQTERM {"type":"source-term","frame":9,"recordId":"dict-af"}'
        ))
        shown = router.consume(
            'DQGLYPH {"type":"record","frame":10,'
            '"recordId":"chr-fc-35e7"}'
        )
        assert shown is not None
        self.assertEqual([item["text"] for item in shown["items"]], [
            "發現了鑰匙。"
        ])
        # A variable field can leave exact coverage below threshold. The
        # positive source match remains authoritative until reset.
        self.assertIsNone(router.consume(
            'DQGLYPH {"type":"coverage","frame":11,'
            '"recordId":"chr-fc-35e7","segments":['
            '{"sourceStart":0,"sourceEndExclusive":7,"visibleCount":0}]}'
        ))
        self.assertIsNone(router.consume(
            'DQGLYPH {"type":"reset","frame":30,'
            '"recordId":"chr-fc-35e7","reason":"coverage-timeout"}'
        ))
        hidden = router.consume(
            'DQGLYPH {"type":"reset","frame":31,'
            '"recordId":"chr-fc-35e7"}'
        )
        assert hidden is not None
        self.assertFalse(hidden["visible"])

    def test_stale_message_instance_cannot_hide_new_lifecycle(self) -> None:
        router = SubtitleEventRouter(
            json.loads(DIALOGUE_TRANSLATIONS.read_text(encoding="utf-8")),
            load_database(DATABASE),
        )
        first = router.consume(
            'DQGLYPH {"type":"record","frame":10,'
            '"recordId":"chr-fc-38a7","instanceId":"msg-1"}'
        )
        assert first is not None
        second = router.consume(
            'DQGLYPH {"type":"record","frame":20,'
            '"recordId":"chr-fc-38a7","instanceId":"msg-2"}'
        )
        assert second is not None
        self.assertIsNone(router.consume(
            'DQGLYPH {"type":"reset","frame":21,'
            '"recordId":"chr-fc-38a7","instanceId":"msg-1"}'
        ))
        hidden = router.consume(
            'DQGLYPH {"type":"reset","frame":30,'
            '"recordId":"chr-fc-38a7","instanceId":"msg-2"}'
        )
        assert hidden is not None
        self.assertFalse(hidden["visible"])

    def test_snapshot_stacks_visible_dialogue_units_without_overlap(self) -> None:
        router = SubtitleEventRouter(
            json.loads(DIALOGUE_TRANSLATIONS.read_text(encoding="utf-8")),
            load_database(DATABASE),
        )
        scene = router.consume(
            'DQGLYPH {"type":"coverage","recordId":"chr-fc-38a7",'
            '"segments":[{"sourceStart":0,"sourceEndExclusive":22,'
            '"visibleCount":22},{"sourceStart":22,"sourceEndExclusive":46,'
            '"visibleCount":24}]}'
        )
        assert scene is not None
        first, second = scene["items"]
        self.assertEqual(first["ppuBounds"]["y"], 168)
        self.assertEqual(first["ppuBounds"]["height"], 15)
        self.assertEqual(second["ppuBounds"]["y"], 183)
        self.assertEqual(second["ppuBounds"]["height"], 15)

    def test_snapshot_keeps_newest_dialogue_suffix_that_fits_box(self) -> None:
        router = SubtitleEventRouter(
            json.loads(DIALOGUE_TRANSLATIONS.read_text(encoding="utf-8")),
            load_database(DATABASE),
        )
        units = [
            unit for unit in router._units_by_id.values()
            if unit.kind == "dialogue" and unit.record_id == "chr-fc-3397"
        ]
        fitted = router._fit_dialogue_units(units[:3], 45)
        self.assertTrue(fitted)
        self.assertLessEqual(
            sum(unit.line_count * (unit.line_height or 0) for unit in fitted),
            45,
        )
        self.assertEqual(fitted[-1], units[2])

    def test_new_overlapping_dialogue_record_replaces_old_record(self) -> None:
        router = SubtitleEventRouter(
            json.loads(DIALOGUE_TRANSLATIONS.read_text(encoding="utf-8")),
            load_database(DATABASE),
        )
        records = {}
        for unit in router._units_by_id.values():
            if unit.kind == "dialogue":
                records.setdefault(unit.record_id, unit)
        overlapping = None
        first = next(iter(records.values()))
        for candidate in records.values():
            if (
                candidate.record_id != first.record_id
                and router._bounds_overlap(first.ppu_bounds, candidate.ppu_bounds)
            ):
                overlapping = candidate
                break
        self.assertIsNotNone(overlapping)
        assert overlapping is not None
        router.apply_visibility(VisibilityUpdate(
            f"dialogue:{first.record_id}", ((first.id, 1),)
        ))
        scene = router.apply_visibility(VisibilityUpdate(
            f"dialogue:{overlapping.record_id}", ((overlapping.id, 1),)
        ))
        self.assertNotIn(first.id, {item["unitId"] for item in scene["items"]})
        self.assertIn(overlapping.id, {item["unitId"] for item in scene["items"]})

    def test_snapshot_trace_load_and_timed_replay(self) -> None:
        snapshots = [
            {
                "frame": 100,
                "visible": True,
                "mode": "visible-translation-snapshot",
                "items": [{"unitId": "one", "text": "交談"}],
                "delta": {"appeared": ["one"], "updated": [],
                          "disappeared": []},
            },
            {
                "frame": 106,
                "visible": False,
                "mode": "visible-translation-snapshot",
                "items": [],
                "delta": {"appeared": [], "updated": [],
                          "disappeared": ["one"]},
            },
        ]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "snapshots.jsonl"
            path.write_text(
                "\n".join(json.dumps(item, ensure_ascii=False) for item in snapshots),
                encoding="utf-8",
            )
            loaded = load_snapshots(path)
        output = io.StringIO()
        delays = []
        replay_snapshots(
            loaded, output, fps=60.0, speed=2.0, sleep=delays.append
        )
        self.assertEqual(delays, [0.05])
        self.assertEqual(
            [json.loads(line) for line in output.getvalue().splitlines()],
            snapshots,
        )

    def test_snapshot_trace_rejects_non_snapshot_lines(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "snapshots.jsonl"
            path.write_text('{"frame":1,"items":[]}\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "line 1"):
                load_snapshots(path)

    def test_snapshot_audit_accepts_balanced_non_overlapping_trace(self) -> None:
        unit = {
            "unitId": "menu#label-1", "recordId": "menu", "text": "交談",
            "ppuBounds": {"x": 8, "y": 8, "width": 32, "height": 12},
            "visibleCount": 4, "totalCount": 4, "visibleRatio": 1.0,
            "fontSize": 7.5,
        }
        snapshots = [
            {"frame": 1, "mode": "visible-translation-snapshot",
             "visible": True, "items": [unit],
             "delta": {"appeared": ["menu#label-1"], "updated": [],
                       "disappeared": []}},
            {"frame": 10, "mode": "visible-translation-snapshot",
             "visible": False, "items": [],
             "delta": {"appeared": [], "updated": [],
                       "disappeared": ["menu#label-1"]}},
        ]
        report = audit_snapshots(snapshots)
        self.assertEqual(report["summary"], {"errors": 0, "warnings": 0})
        self.assertIn("No issues found", render_markdown(report))

    def test_snapshot_audit_reports_schema_delta_overlap_and_flicker(self) -> None:
        first = {
            "unitId": "one", "recordId": "menu", "text": "一",
            "ppuBounds": {"x": 250, "y": 0, "width": 10, "height": 8},
            "visibleCount": 2, "totalCount": 1, "visibleRatio": 0.5,
            "fontSize": 7.5,
        }
        second = {
            **first, "unitId": "two",
            "ppuBounds": {"x": 248, "y": 0, "width": 8, "height": 8},
            "visibleCount": 1, "visibleRatio": 1.0,
        }
        snapshots = [
            {"frame": 1, "mode": "visible-translation-snapshot",
             "visible": True, "items": [first, second], "delta": {}},
            {"frame": 2, "mode": "visible-translation-snapshot",
             "visible": False, "items": [],
             "delta": {"appeared": [], "updated": [],
                       "disappeared": ["one", "two"]}},
            {"frame": 3, "mode": "visible-translation-snapshot",
             "visible": True, "items": [second],
             "delta": {"appeared": ["two"], "updated": [],
                       "disappeared": []}},
        ]
        report = audit_snapshots(snapshots)
        codes = {finding["code"] for finding in report["findings"]}
        self.assertTrue({"out-of-bounds", "invalid-coverage", "overlap",
                         "delta-mismatch", "flicker", "visible-at-end"} <= codes)

    def test_snapshot_lifecycle_regression_fixture_is_clean(self) -> None:
        snapshots = load_snapshots(SNAPSHOT_LIFECYCLE)
        self.assertEqual(len(snapshots), 6)
        self.assertEqual(
            [snapshot["frame"] for snapshot in snapshots],
            [1, 10, 20, 30, 40, 50],
        )
        report = audit_snapshots(snapshots)
        self.assertEqual(report["summary"], {"errors": 0, "warnings": 0})
        self.assertEqual(report["recordIds"], ["dialogue", "menu", "status"])

    def test_glyph_provenance_script_contains_catalog_positions(self) -> None:
        catalog = json.loads((
            ROOT / "Research/dragon-quest-jp/generated/dialogue-catalog-validated.json"
        ).read_text(encoding="utf-8"))
        translations = json.loads(DIALOGUE_TRANSLATIONS.read_text(encoding="utf-8"))
        dictionary_catalog = json.loads((
            ROOT / "Research/dragon-quest-jp/generated/prg-dictionary-catalog.json"
        ).read_text(encoding="utf-8"))
        vocabulary = json.loads(VOCABULARY_TRANSLATIONS.read_text(encoding="utf-8"))
        template = (
            ROOT / "Research/dragon-quest-jp/runtime/dialogue-glyph-provenance.lua"
        ).read_text(encoding="utf-8")
        script = build_glyph_provenance_script(
            catalog, translations, load_character_map(CHARACTER_MAP), template,
            database=load_database(DATABASE),
            dictionary_catalog=dictionary_catalog,
            vocabulary=vocabulary,
        )
        self.assertNotIn("__NES_TRANSLATION_GLYPH_PROVENANCE_CONFIG__", script)
        self.assertIn('id = "chr-fc-38a7"', script)
        self.assertIn("expandedIndex = 0", script)
        self.assertIn("sourceEndExclusive = 90", script)
        self.assertIn("emptyGraceFrames = 20", script)
        self.assertIn("local nextInstanceNumber = 1", script)
        self.assertIn('activeInstanceId = "msg-"', script)
        self.assertIn("characterId = activeInstanceId", script)
        self.assertIn('\\"type\\":\\"instance-begin\\"', script)
        self.assertIn('\\"type\\":\\"instance-end\\"', script)
        self.assertNotIn("stableFrames", script)
        self.assertIn("propagateCopiedCells()", script)
        self.assertIn("emitTextRuns()", script)
        self.assertIn('DQRUN {\\"type\\":\\"writes\\"', script)
        self.assertIn('\\"type\\":\\"copy\\"', script)
        self.assertIn("delta % 32 == 0", script)
        self.assertIn("assignCell(destination, cell)", script)
        self.assertIn("labelIndex = labelIndex", script)
        self.assertIn("startX = 128, endX = 160", script)
        self.assertIn(
            "sourceStartAddress = 33883, sourceEndAddress = 33885", script
        )
        self.assertIn('state["ppu.tmpVideoRamAddr"]', script)
        self.assertIn('state["ppu.xScroll"]', script)
        self.assertIn("local function physicalNametableAddress", script)
        self.assertIn("return ppuAddress % 0x800", script)
        self.assertIn(
            "layoutPending[physicalNametableAddress(candidate.ppuAddress)]",
            script,
        )
        self.assertIn("candidate.value == layoutSourceValue", script)
        self.assertIn('\\"reason\\":\\"coverage-timeout\\"', script)
        self.assertIn('DQTERM {\\"type\\":\\"source-term\\"', script)
        self.assertIn('id = "dict-a1"', script)
        self.assertIn("dynamic = true", script)
        self.assertNotIn('id = "dict-bb"', script)

    def test_character_map_renders_dialogue_and_combines_dakuten(self) -> None:
        character_map = load_character_map(CHARACTER_MAP)
        self.assertEqual(character_map[0xF2]["confidence"], "runtime-confirmed")
        rendered = render_bytes(
            [0x55, 0x62, 0x19, 0x24, 0xF8, 0xFE, 0xF2, 0x2F, 0x61, 0xFC],
            character_map,
        )
        self.assertEqual(rendered, "＊「たび\n{PLAYER_NAME}よ！<END>")

    def test_dictionary_expansion_preserves_source_provenance(self) -> None:
        dictionary = (bytes((0x55, 0x62)), bytes((0x24, 0xF8)))
        result = expand_tokens(
            bytes((0x6D, 0x10, 0x6E, 0xFC)),
            dictionary,
            0x6D,
            source_offset=0x3300,
            modifier_values=frozenset((0xF8,)),
        )
        self.assertEqual(result[0].source_offset, 0x3300)
        self.assertEqual(result[0].dictionary_index, 0)
        self.assertEqual(result[0].expanded, (0x55, 0x62))
        self.assertEqual(result[1].kind, "glyph")
        self.assertEqual(result[2].dictionary_index, 1)
        self.assertEqual(result[3].kind, "control")

    def test_dragon_quest_dictionary_expands_runtime_record(self) -> None:
        rom = ROM.read_bytes()
        layout = ines_chr_layout(rom)
        source = rom[
            layout.file_offset + 0x3397:layout.file_offset + 0x33C1
        ]
        dictionary = read_dictionary(ines_prg(rom), 0x0858, 0x0B21, 0xFA)
        self.assertEqual(len(dictionary), 123)
        result = expand_tokens(
            source,
            dictionary,
            0x6D,
            source_offset=0x3397,
            modifier_values=frozenset((0xF8,)),
        )
        self.assertEqual(result[0].expanded, (0x55, 0x62))
        self.assertEqual(result[2].value, 0xE7)
        self.assertEqual(result[2].expanded, (0x24, 0xF8))
        self.assertEqual(result[-1].value, 0xFC)
        self.assertEqual(result[-1].kind, "control")

    def test_chr_record_splitter_preserves_offsets_and_unknown_bytes(self) -> None:
        header = bytearray(b"NES\x1a" + bytes(12))
        header[4] = 1
        header[5] = 1
        prg = bytes(16 * 1024)
        chr_data = bytes((0xAA, 0xFC, 0x01, 0xE7, 0xFC)) + bytes(8187)
        rom = bytes(header) + prg + chr_data
        layout = ines_chr_layout(rom)
        self.assertEqual(layout.file_offset, 16 + 16 * 1024)
        records = split_chr_records(rom, 0xFC, maximum_length=8)
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].chr_start, 0)
        self.assertEqual(records[0].raw_hex, "aa fc")
        self.assertEqual(records[1].chr_start, 2)
        self.assertEqual(records[1].raw_hex, "01 e7 fc")

    def test_dragon_quest_runtime_chr_record_is_reproducible(self) -> None:
        records = split_chr_records(
            ROM.read_bytes(), 0xFC, minimum_length=2, maximum_length=256
        )
        record = next(item for item in records if item.chr_start == 0x3397)
        self.assertEqual(record.chr_end_exclusive, 0x33C1)
        self.assertTrue(record.raw_hex.startswith("6d 19 e7 22 15 19 11 d7"))
        self.assertTrue(record.raw_hex.endswith("fc"))

    def test_dialogue_catalog_ranks_confirmed_record_without_dropping_bytes(self) -> None:
        catalog = build_catalog(
            ROM.read_bytes(),
            dictionary_start=0x0858,
            dictionary_end=0x0B21,
            dictionary_terminator=0xFA,
            token_base=0x6D,
            record_terminator=0xFC,
            character_map=load_character_map(CHARACTER_MAP),
            modifier_values=frozenset((0xF8,)),
        )
        record = next(
            item for item in catalog["records"] if item["id"] == "chr-fc-3397"
        )
        self.assertEqual(record["source"]["chrEndExclusive"], 0x33C1)
        self.assertEqual(record["evidence"]["likelihood"], "high")
        self.assertEqual(record["unknownBytes"], [])
        self.assertEqual(record["decoded"].splitlines()[0], "＊「たびのしたくが できたなら")
        self.assertEqual(
            len(bytes.fromhex(record["rawHex"])),
            record["metrics"]["sourceByteCount"],
        )
        shared_shop = next(
            item for item in catalog["records"] if item["id"] == "chr-fc-22c4"
        )
        self.assertEqual(shared_shop["messageUnitCount"], 4)
        self.assertEqual(
            [unit["id"] for unit in shared_shop["messageUnits"]],
            [
                "chr-fc-22c4-u1", "chr-fc-22c4-u2",
                "chr-fc-22c4-u3", "chr-fc-22c4-u4",
            ],
        )
        self.assertEqual(
            [unit["separatorHex"] for unit in shared_shop["messageUnits"]],
            ["fe 57 ff", "fe 57 ff", "fe 57 ff", ""],
        )
        self.assertEqual(
            shared_shop["messageUnits"][2]["decoded"],
            "＊「おかねが たりませんが<4F>",
        )
        review = render_catalog_review(catalog, {"high"})
        self.assertIn("chr-fc-3397 — high", review)
        self.assertNotIn("chr-fc-0000", review)

    def test_runtime_windows_match_catalog_only_when_addresses_are_contiguous(self) -> None:
        events = []
        for offset, value in enumerate((0x55, 0x62, 0xFC)):
            events.extend((
                {
                    "type": "chr-text-window",
                    "frame": 10 + offset,
                    "selector": 191,
                    "ppuAddress": 0x1397 + offset,
                },
                {
                    "type": "chr-text-byte",
                    "frame": 10 + offset,
                    "ramAddress": 0x03B0,
                    "value": value,
                },
                {
                    "type": "chr-text-byte",
                    "frame": 10 + offset,
                    "ramAddress": 0x03B1,
                    "value": 0xAA,
                },
            ))
        runtime_bytes = extract_runtime_bytes(events)
        catalog = {
            "records": [{
                "id": "chr-fc-test",
                "rawHex": "55 62 fc",
                "decoded": "＊「<END>",
                "evidence": {"likelihood": "high"},
            }]
        }
        hits = match_catalog(runtime_bytes, catalog)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["ppuStart"], 0x1397)
        self.assertEqual(hits[0]["confidence"], "runtime-confirmed")
        self.assertEqual(hits[0]["runtimeStartIndex"], 0)
        self.assertEqual(hits[0]["runtimeEndExclusive"], 3)

        broken = list(events)
        broken[6]["ppuAddress"] = 0x1400
        self.assertEqual(match_catalog(extract_runtime_bytes(broken), catalog), [])

    def test_runtime_matches_promote_catalog_record_and_count_occurrences(self) -> None:
        catalog = {
            "records": [{
                "id": "chr-fc-test",
                "runtime": {
                    "status": "unverified",
                    "observedReadAddress": None,
                    "notes": None,
                },
            }]
        }
        hit = {
            "recordId": "chr-fc-test",
            "frameStart": 10,
            "frameEnd": 20,
            "selector": 1,
            "ppuStart": 0x1234,
            "ppuEndExclusive": 0x1237,
        }
        validated = apply_runtime_matches(
            catalog,
            ({"trace": "one.jsonl", "hits": [hit, dict(hit)]},),
        )
        runtime = validated["records"][0]["runtime"]
        self.assertEqual(runtime["status"], "runtime-confirmed")
        self.assertEqual(runtime["occurrenceCount"], 2)
        self.assertEqual(runtime["observedReadAddress"], 0x1234)
        self.assertEqual(
            validated["validationSummary"]["runtimeConfirmedRecordCount"], 1
        )
        self.assertEqual(catalog["records"][0]["runtime"]["status"], "unverified")

    def test_dialogue_decoder_instruction_addresses_match_rom(self) -> None:
        self.assertEqual(
            bytes(prg_byte(address) for address in range(0xBD30, 0xBD32)),
            bytes((0xB1, 0x99)),  # LDA ($99),Y
        )
        self.assertEqual(
            bytes(prg_byte(address) for address in range(0xBE6A, 0xBE6C)),
            bytes((0xC9, 0x6D)),  # CMP #$6D
        )
        self.assertEqual(
            bytes(prg_byte(address) for address in range(0xBEF2, 0xBEF4)),
            bytes((0xB1, 0x99)),  # LDA ($99),Y
        )
        self.assertEqual(
            bytes(prg_byte(address) for address in range(0xC433, 0xC435)),
            bytes((0x06, 0x3C)),  # ASL $3C after selector setup
        )
        self.assertEqual(
            bytes(prg_byte(address) for address in range(0xC498, 0xC49A)),
            bytes((0xA5, 0x99)),  # begin glyph PPU-address adjustment
        )

    def test_clusters_contiguous_prg_reads_and_excludes_known_range(self) -> None:
        items = [
            {"type": "rom-read", "frame": 10, "cpuAddress": 0x8459,
             "prgOffset": 0x0459, "cpuPc": 1},
            {"type": "rom-read", "frame": 20, "cpuAddress": 0x9000,
             "prgOffset": 0x1000, "cpuPc": 2},
            {"type": "rom-read", "frame": 20, "cpuAddress": 0x9001,
             "prgOffset": 0x1001, "cpuPc": 2},
            {"type": "rom-read", "frame": 21, "cpuAddress": 0x9001,
             "prgOffset": 0x1001, "cpuPc": 3},
            {"type": "input", "frame": 22, "buttons": 1},
        ]
        clusters = cluster_reads(items, excluded=((0x0459, 0x049B),))
        self.assertEqual(len(clusters), 1)
        self.assertEqual(clusters[0].start, 0x1000)
        self.assertEqual(clusters[0].end_exclusive, 0x1002)
        self.assertEqual(clusters[0].read_count, 3)
        self.assertEqual(clusters[0].frames, (20, 21))
        self.assertEqual(clusters[0].cpu_pcs, (2, 3))

        narrowed = cluster_reads(items, frame_from=21, frame_to=21)
        self.assertEqual(len(narrowed), 1)
        self.assertEqual(narrowed[0].start, 0x1001)
        self.assertEqual(narrowed[0].read_count, 1)

    def test_instruction_operand_reads_are_not_text_candidates(self) -> None:
        items = [{
            "type": "rom-read",
            "frame": 1,
            "cpuAddress": 0xB001,
            "prgOffset": 0x3001,
            "cpuPc": 0xB000,
        }]
        self.assertEqual(cluster_reads(items), [])


class ResolverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.database = load_database(DATABASE)
        self.resolver = TextResolver(self.database)

    def test_unknown_read_does_not_trigger(self) -> None:
        self.assertEqual(self.resolver.consume(read_event(0x1000)), [])

    def test_record_read_triggers_once(self) -> None:
        first = self.resolver.consume(read_event(0x0459, 10))
        repeated = self.resolver.consume(read_event(0x045A, 11))
        self.assertEqual(len(first), 1)
        self.assertEqual(first[0].type, "text-show")
        self.assertEqual(first[0].record_id, "dq.menu.main")
        self.assertEqual(repeated, [])

    def test_hide_allows_record_to_trigger_again(self) -> None:
        first = self.resolver.consume(read_event(0x0459, 10))[0]
        hidden = self.resolver.hide(20)[0]
        second = self.resolver.consume(read_event(0x0459, 30))[0]
        self.assertEqual(hidden.type, "text-hide")
        self.assertNotEqual(first.instance_id, second.instance_id)

    def test_record_declared_dismiss_input_hides_active_text(self) -> None:
        self.resolver.consume(read_event(0x0459, 10))
        ignored = self.resolver.consume(InputEvent("input", 20, 0x01))
        hidden = self.resolver.consume(InputEvent("input", 30, 0x02))
        self.assertEqual(ignored, [])
        self.assertEqual(len(hidden), 1)
        self.assertEqual(hidden[0].type, "text-hide")
        self.assertEqual(hidden[0].frame, 30)

    def test_strength_dismiss_hides_when_game_closes_all_menus(self) -> None:
        main = self.resolver.consume(read_event(0x0459, 10))[0]
        strength = self.resolver.consume(read_event(0x030F, 20))[0]
        hidden = self.resolver.consume(InputEvent("input", 30, 0x02))[0]
        self.assertEqual(main.type, "text-show")
        self.assertEqual(strength.type, "text-replace")
        self.assertEqual(strength.record_id, "dq.menu.strength")
        self.assertEqual(hidden.type, "text-hide")
        self.assertEqual(hidden.record_id, "dq.menu.strength")

    def test_child_record_can_restore_declared_parent(self) -> None:
        value = json.loads(DATABASE.read_text(encoding="utf-8"))
        value["records"][1]["deactivation"]["returnToRecordId"] = "dq.menu.main"
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "database.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            resolver = TextResolver(load_database(path))
        resolver.consume(read_event(0x0459, 10))
        resolver.consume(read_event(0x030F, 20))
        restored = resolver.consume(InputEvent("input", 30, 0x02))[0]
        self.assertEqual(restored.type, "text-replace")
        self.assertEqual(restored.record_id, "dq.menu.main")
        self.assertIsNone(restored.evidence_prg_offset)

    def test_dismiss_input_without_active_text_is_ignored(self) -> None:
        self.assertEqual(
            self.resolver.consume(InputEvent("input", 20, 0x02)),
            [],
        )

    def test_renderer_only_consumes_text_event(self) -> None:
        event = self.resolver.consume(read_event(0x0459))[0]
        command = DebugRenderer(self.database).consume(event)
        self.assertEqual(command.type, "show")
        self.assertEqual(command.text, "交谈　　　咒文\n状态　　　道具\n楼梯　　　调查\n开门　　　拿取")

    def test_synthetic_trace_is_deterministic(self) -> None:
        first = replay(DATABASE, TRACE)
        second = replay(DATABASE, TRACE)
        self.assertEqual(first, second)
        self.assertEqual([item["type"] for item in first], ["show", "hide", "show"])

    def test_replay_ignores_diagnostic_capture_events(self) -> None:
        lines = [
            {"type": "capture-start", "frame": 1},
            {"type": "record-hit", "frame": 2, "recordId": "candidate"},
            {"type": "rom-read", "frame": 3, "cpuAddress": 0x8459,
             "prgOffset": 0x0459, "value": 0x3C, "cpuPc": 0xC000},
            {"type": "capture-stop", "frame": 4},
        ]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "diagnostic.jsonl"
            path.write_text(
                "\n".join(json.dumps(item) for item in lines),
                encoding="utf-8",
            )
            result = replay(DATABASE, path)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["type"], "show")
        self.assertEqual(result[0]["record_id"], "dq.menu.main")

    def test_mesen_trace_line_contract(self) -> None:
        event = parse_trace_line(
            'DQTRACE {"type":"rom-read","frame":42,"cpuAddress":33881,'
            '"prgOffset":1113,"value":60,"cpuPc":49152}'
        )
        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.prg_offset, 0x0459)
        self.assertEqual(event.frame, 42)
        self.assertIsNone(parse_trace_line("ordinary Mesen log"))

        input_event = parse_trace_line(
            'DQTRACE {"type":"input","frame":43,"buttons":2}'
        )
        self.assertEqual(input_event, InputEvent("input", 43, 2))

    def test_diagnostic_trace_payload_contract(self) -> None:
        item = parse_trace_payload(
            'DQTRACE {"type":"ram-write","frame":43,"address":17,'
            '"value":2,"cpuPc":49154}'
        )
        self.assertEqual(item, {
            "type": "ram-write",
            "frame": 43,
            "address": 17,
            "value": 2,
            "cpuPc": 49154,
        })
        self.assertIsNone(parse_trace_line(
            'DQTRACE {"type":"ram-write","frame":43,"address":17,'
            '"value":2,"cpuPc":49154}'
        ))

        state = parse_trace_payload(
            'DQTRACE {"type":"state","frame":44,"menuMode":3,'
            '"input":1,"textLo":89,"textHi":132,"values":[3,1,89,132]}'
        )
        assert state is not None
        self.assertEqual(state["type"], "state")
        self.assertEqual(state["input"], 1)


if __name__ == "__main__":
    unittest.main()
