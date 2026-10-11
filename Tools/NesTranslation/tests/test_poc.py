from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from Tools.NesTranslation.database import DatabaseError, load_database, validate_rom
from Tools.NesTranslation.analyze_reads import cluster_reads
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


class ReadAnalysisTests(unittest.TestCase):
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
