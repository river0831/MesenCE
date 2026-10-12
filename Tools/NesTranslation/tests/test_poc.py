from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from Tools.NesTranslation.database import DatabaseError, load_database, validate_rom
from Tools.NesTranslation.analyze_reads import cluster_reads
from Tools.NesTranslation.chr_records import ines_chr_layout, split_chr_records
from Tools.NesTranslation.display import DebugRenderer
from Tools.NesTranslation.events import InputEvent, RomReadEvent
from Tools.NesTranslation.live import parse_trace_line, parse_trace_payload
from Tools.NesTranslation.overlay import build_overlay_script
from Tools.NesTranslation.provenance import build_provenance_script
from Tools.NesTranslation.replay import replay
from Tools.NesTranslation.resolver import TextResolver


ROOT = Path(__file__).parents[3]
DATABASE = ROOT / "Research/dragon-quest-jp/database/game-database.json"
ROM = ROOT / "test_roms/Dragon Quest (Japan).nes"
TRACE = ROOT / "Research/dragon-quest-jp/traces/main-menu-synthetic.jsonl"


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


class ReadAnalysisTests(unittest.TestCase):
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
