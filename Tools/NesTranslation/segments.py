"""Generic source-aligned translation segment primitives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .database import DatabaseError


@dataclass(frozen=True, order=True)
class SegmentRange:
    start: int
    end_exclusive: int

    def __post_init__(self) -> None:
        if self.start < 0 or self.end_exclusive <= self.start:
            raise ValueError("segment range must be positive")

    def contains(self, source_index: int) -> bool:
        return self.start <= source_index < self.end_exclusive


@dataclass(frozen=True)
class TranslationSegment:
    id: str
    ranges: tuple[SegmentRange, ...]
    lines: tuple[str, ...]
    confidence: str | None = None

    @property
    def total_count(self) -> int:
        return sum(item.end_exclusive - item.start for item in self.ranges)

    def visible_count(self, source_indices: Iterable[int]) -> int:
        return sum(
            1 for index in set(source_indices)
            if any(item.contains(index) for item in self.ranges)
        )

    def contains(self, source_index: int) -> bool:
        return any(item.contains(source_index) for item in self.ranges)


def parse_segment(raw: dict[str, Any], *, fallback_id: str) -> TranslationSegment:
    """Accept legacy contiguous ranges and new multi-range segments."""
    segment_id = raw.get("id", fallback_id)
    if not isinstance(segment_id, str) or not segment_id:
        raise DatabaseError("translation segment id must be a non-empty string")
    raw_ranges = raw.get("sourceRanges")
    if raw_ranges is None:
        raw_ranges = [{
            "start": raw.get("sourceStart"),
            "endExclusive": raw.get("sourceEndExclusive"),
        }]
    if not isinstance(raw_ranges, list) or not raw_ranges:
        raise DatabaseError(f"translation segment ranges must be non-empty: {segment_id}")
    ranges: list[SegmentRange] = []
    for index, item in enumerate(raw_ranges):
        if not isinstance(item, dict):
            raise DatabaseError(f"segment range must be an object: {segment_id}[{index}]")
        try:
            value = SegmentRange(item.get("start"), item.get("endExclusive"))
        except (TypeError, ValueError) as error:
            raise DatabaseError(
                f"invalid translation segment range: {segment_id}[{index}]"
            ) from error
        if ranges and value.start < ranges[-1].end_exclusive:
            raise DatabaseError(f"overlapping ranges within segment: {segment_id}")
        ranges.append(value)
    lines = raw.get("lines")
    if (
        not isinstance(lines, list) or not lines
        or not all(isinstance(line, str) and line for line in lines)
    ):
        raise DatabaseError(f"translation segment lines must be non-empty: {segment_id}")
    confidence = raw.get("confidence")
    if confidence is not None and not isinstance(confidence, str):
        raise DatabaseError(f"translation segment confidence must be a string: {segment_id}")
    return TranslationSegment(
        id=segment_id, ranges=tuple(ranges), lines=tuple(lines),
        confidence=confidence,
    )


def parse_record_segments(record: dict[str, Any]) -> tuple[TranslationSegment, ...]:
    record_id = record.get("id", "unknown")
    raw_segments = record.get("segments")
    if not isinstance(raw_segments, list) or not raw_segments:
        raise DatabaseError(f"translation segments must be non-empty: {record_id}")
    result = tuple(
        parse_segment(raw, fallback_id=f"{record_id}#{index}")
        for index, raw in enumerate(raw_segments)
        if isinstance(raw, dict)
    )
    if len(result) != len(raw_segments):
        raise DatabaseError(f"translation segment must be an object: {record_id}")
    ids = [segment.id for segment in result]
    if len(ids) != len(set(ids)):
        raise DatabaseError(f"duplicate translation segment id: {record_id}")
    occupied: list[tuple[SegmentRange, str]] = []
    for segment in result:
        for item in segment.ranges:
            for other, other_id in occupied:
                if item.start < other.end_exclusive and other.start < item.end_exclusive:
                    raise DatabaseError(
                        f"translation segment ranges overlap: {segment.id} and {other_id}"
                    )
            occupied.append((item, segment.id))
    return result


def select_segment_by_visible_source(
    segments: Iterable[TranslationSegment], visible_indices: Iterable[int]
) -> TranslationSegment | None:
    """Choose the segment owning the newest visible source position."""
    indices = tuple(visible_indices)
    if not indices:
        return None
    newest = max(indices)
    return next((segment for segment in segments if segment.contains(newest)), None)
