from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from Tools.NesTranslation.database import DatabaseError, load_database, validate_rom
from Tools.NesTranslation.display import DebugRenderer
from Tools.NesTranslation.events import InputEvent, RomReadEvent
from Tools.NesTranslation.live import parse_trace_line, parse_trace_payload
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
