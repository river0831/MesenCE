"""Generic runtime model for one execution of a translated message."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal


class InstanceState(str, Enum):
    ACTIVE = "active"
    CLOSED = "closed"


SourceRole = Literal["template", "shared", "parameter", "unknown"]
CharacterSource = Literal["template", "parameter", "shared", "inferred"]


@dataclass(frozen=True)
class SourceSpan:
    """One contiguous part of the execution-time source read trace."""

    bank: int | None
    start: int
    end_exclusive: int
    role: SourceRole = "template"

    def __post_init__(self) -> None:
        if self.start < 0 or self.end_exclusive <= self.start:
            raise ValueError("source span must have a positive range")


@dataclass(frozen=True)
class GlyphComponent:
    """One physical tile used to display a logical character."""

    value: int
    role: Literal["whole", "base", "mark"] = "whole"

    def __post_init__(self) -> None:
        if not 0 <= self.value <= 0xFF:
            raise ValueError("glyph component value must fit in one byte")


@dataclass(frozen=True)
class LogicalCharacter:
    """A character emitted by a message, before it reaches the Nametable."""

    id: str
    instance_id: str
    index: int
    display: str
    source_offset: int | None
    source_type: CharacterSource
    parameter_slot: str | None = None
    components: tuple[GlyphComponent, ...] = ()

    def __post_init__(self) -> None:
        if not self.id or not self.instance_id or self.index < 0:
            raise ValueError("logical character identity must be valid")
        if self.source_type == "parameter" and not self.parameter_slot:
            raise ValueError("parameter characters require a parameter slot")
        if self.source_type != "parameter" and self.parameter_slot is not None:
            raise ValueError("only parameter characters may name a parameter slot")


@dataclass
class ParameterInstance:
    """A runtime value inserted into a static message template."""

    slot: str
    value_id: int | None = None
    source_text: str = ""
    character_ids: list[str] = field(default_factory=list)
    source_spans: list[SourceSpan] = field(default_factory=list)


@dataclass
class MessageInstance:
    """One lifecycle of one static translation record."""

    id: str
    record_id: str
    start_frame: int
    last_activity_frame: int
    state: InstanceState = InstanceState.ACTIVE
    end_frame: int | None = None
    source_spans: list[SourceSpan] = field(default_factory=list)
    parameters: dict[str, ParameterInstance] = field(default_factory=dict)
    characters: list[LogicalCharacter] = field(default_factory=list)

    def add_source_byte(
        self, address: int, *, bank: int | None = None,
        role: SourceRole = "template", frame: int | None = None,
    ) -> None:
        """Append one observed read, merging only truly contiguous reads."""
        self._require_active()
        if address < 0:
            raise ValueError("source address must be non-negative")
        if frame is not None:
            self.last_activity_frame = max(self.last_activity_frame, frame)
        if self.source_spans:
            previous = self.source_spans[-1]
            if (
                previous.bank == bank
                and previous.role == role
                and previous.end_exclusive == address
            ):
                self.source_spans[-1] = SourceSpan(
                    bank, previous.start, address + 1, role
                )
                return
        self.source_spans.append(SourceSpan(bank, address, address + 1, role))

    def ensure_parameter(
        self, slot: str, *, value_id: int | None = None
    ) -> ParameterInstance:
        self._require_active()
        if not slot:
            raise ValueError("parameter slot must not be empty")
        parameter = self.parameters.get(slot)
        if parameter is None:
            parameter = ParameterInstance(slot=slot, value_id=value_id)
            self.parameters[slot] = parameter
        elif value_id is not None:
            if parameter.value_id is not None and parameter.value_id != value_id:
                raise ValueError("parameter slot cannot change value in one instance")
            parameter.value_id = value_id
        return parameter

    def add_character(
        self, display: str, *, source_offset: int | None,
        source_type: CharacterSource = "template",
        parameter_slot: str | None = None,
        components: tuple[GlyphComponent, ...] = (),
        frame: int | None = None,
    ) -> LogicalCharacter:
        self._require_active()
        index = len(self.characters)
        character = LogicalCharacter(
            id=f"{self.id}:{index}", instance_id=self.id, index=index,
            display=display, source_offset=source_offset,
            source_type=source_type, parameter_slot=parameter_slot,
            components=components,
        )
        self.characters.append(character)
        if frame is not None:
            self.last_activity_frame = max(self.last_activity_frame, frame)
        if parameter_slot is not None:
            parameter = self.ensure_parameter(parameter_slot)
            parameter.character_ids.append(character.id)
            parameter.source_text += display
        return character

    def close(self, frame: int) -> None:
        self._require_active()
        if frame < self.start_frame:
            raise ValueError("instance cannot end before it starts")
        self.last_activity_frame = max(self.last_activity_frame, frame)
        self.end_frame = frame
        self.state = InstanceState.CLOSED

    def _require_active(self) -> None:
        if self.state is not InstanceState.ACTIVE:
            raise ValueError("message instance is already closed")


class MessageInstanceTracker:
    """Allocate independent lifecycles for reusable static records."""

    def __init__(self) -> None:
        self._next_id = 1
        self._instances: dict[str, MessageInstance] = {}

    @property
    def instances(self) -> tuple[MessageInstance, ...]:
        return tuple(self._instances.values())

    def begin(self, record_id: str, frame: int) -> MessageInstance:
        if not record_id or frame < 0:
            raise ValueError("record id and start frame must be valid")
        instance_id = f"msg-{self._next_id}"
        self._next_id += 1
        instance = MessageInstance(
            id=instance_id, record_id=record_id,
            start_frame=frame, last_activity_frame=frame,
        )
        self._instances[instance_id] = instance
        return instance

    def get(self, instance_id: str) -> MessageInstance:
        try:
            return self._instances[instance_id]
        except KeyError as error:
            raise KeyError(f"unknown message instance: {instance_id}") from error
