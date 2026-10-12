"""Normalized database read model for independently visible translations."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

from .database import DatabaseError, GameDatabase


@dataclass(frozen=True)
class PpuBounds:
    """A rectangle in the NES 256x240 viewport."""

    x: int
    y: int
    width: int
    height: int

    def as_dict(self) -> dict[str, int]:
        return asdict(self)


@dataclass(frozen=True)
class TextUnit:
    """One translated unit addressable by current PPU visibility."""

    id: str
    record_id: str
    kind: Literal["label", "dialogue", "vocabulary"]
    text: str
    ppu_bounds: PpuBounds
    total_count: int
    font_size: float
    source_index: int | None = None
    source_start: int | None = None
    source_end_exclusive: int | None = None
    line_count: int = 1
    line_height: int | None = None

    def snapshot_item(
        self, visible_count: int, ppu_bounds: PpuBounds | None = None
    ) -> dict[str, Any]:
        item: dict[str, Any] = {
            "unitId": self.id,
            "recordId": self.record_id,
            "text": self.text,
            "ppuBounds": (ppu_bounds or self.ppu_bounds).as_dict(),
            "visibleCount": visible_count,
            "totalCount": self.total_count,
            "visibleRatio": min(visible_count / self.total_count, 1.0),
            "fontSize": self.font_size,
        }
        if self.source_start is not None:
            item["sourceStart"] = self.source_start
        if self.source_end_exclusive is not None:
            item["sourceEndExclusive"] = self.source_end_exclusive
        return item


@dataclass(frozen=True)
class VisibilityUpdate:
    """Complete current visibility for one independently updated source scope."""

    scope_id: str
    unit_counts: tuple[tuple[str, int], ...]
    unit_bounds: tuple[tuple[str, PpuBounds], ...] = ()

    def __post_init__(self) -> None:
        ids = [unit_id for unit_id, _ in self.unit_counts]
        bound_ids = [unit_id for unit_id, _ in self.unit_bounds]
        if not self.scope_id:
            raise ValueError("visibility scope must not be empty")
        if len(ids) != len(set(ids)):
            raise ValueError("visibility update contains duplicate unit IDs")
        if any(not unit_id or count <= 0 for unit_id, count in self.unit_counts):
            raise ValueError("visible unit IDs and counts must be positive")
        if len(bound_ids) != len(set(bound_ids)) or set(bound_ids) - set(ids):
            raise ValueError("visibility bounds must reference unique visible unit IDs")


def build_text_units(
    translations: dict[str, Any], database: GameDatabase | None = None,
    vocabulary: dict[str, Any] | None = None,
) -> tuple[TextUnit, ...]:
    """Normalize label records and reviewed dialogue segments."""
    units: list[TextUnit] = []
    for record in database.records if database else ():
        if record.presentation is None:
            continue
        for index, label in enumerate(record.presentation.labels, 1):
            total = (
                ((label.clear.width + 7) // 8)
                * ((label.clear.height + 7) // 8)
            )
            units.append(TextUnit(
                id=f"{record.id}#label-{index}",
                record_id=record.id,
                kind="label",
                text=label.text,
                ppu_bounds=PpuBounds(
                    label.clear.x, label.clear.y,
                    label.clear.width, label.clear.height,
                ),
                total_count=total,
                font_size=7.5,
                source_index=index,
            ))
    for record in translations.get("records", []):
        box = record["box"]
        for segment in record.get("segments", []):
            start = segment["sourceStart"]
            end = segment["sourceEndExclusive"]
            lines = segment["lines"]
            units.append(TextUnit(
                id=f"{record['id']}#glyph-{start}-{end}",
                record_id=record["id"],
                kind="dialogue",
                text="\n".join(lines),
                ppu_bounds=PpuBounds(
                    box["x"], box["y"], box["width"], box["height"]
                ),
                total_count=end - start,
                font_size=8.5,
                source_start=start,
                source_end_exclusive=end,
                line_count=len(lines),
                line_height=box["lineHeight"],
            ))
    for record in (vocabulary or {}).get("records", []):
        if record.get("category") == "system-template":
            continue
        source_text = str(record.get("sourceText", ""))
        units.append(TextUnit(
            id=f"{record['id']}#vocabulary",
            record_id=record["id"],
            kind="vocabulary",
            text=record["display"],
            ppu_bounds=PpuBounds(0, 0, 8, 8),
            total_count=max(len(source_text), 1),
            font_size=7.5,
        ))
    ids = [unit.id for unit in units]
    if len(ids) != len(set(ids)):
        raise DatabaseError("duplicate normalized text unit id")
    return tuple(units)
