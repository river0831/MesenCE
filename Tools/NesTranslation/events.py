"""Stable event contracts between runtime capture, resolution, and display."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal


@dataclass(frozen=True)
class RomReadEvent:
    type: Literal["rom-read"]
    frame: int
    cpu_address: int
    prg_offset: int
    value: int
    cpu_pc: int


@dataclass(frozen=True)
class TextEvent:
    type: Literal["text-show", "text-replace", "text-hide"]
    frame: int
    record_id: str | None
    instance_id: int | None
    evidence_prg_offset: int | None


def event_dict(event: RomReadEvent | TextEvent) -> dict:
    result = asdict(event)
    result["cpuAddress"] = result.pop("cpu_address", None)
    result["prgOffset"] = result.pop("prg_offset", None)
    result["cpuPc"] = result.pop("cpu_pc", None)
    result["recordId"] = result.pop("record_id", None)
    result["instanceId"] = result.pop("instance_id", None)
    result["evidencePrgOffset"] = result.pop("evidence_prg_offset", None)
    return {key: value for key, value in result.items() if value is not None}
