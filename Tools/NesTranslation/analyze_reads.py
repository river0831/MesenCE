"""Summarize physical PRG ranges observed in a runtime JSONL trace."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ReadCluster:
    start: int
    end_exclusive: int
    read_count: int
    frames: tuple[int, ...]
    cpu_pcs: tuple[int, ...]


def cluster_reads(
    items: list[dict],
    excluded: tuple[tuple[int, int], ...] = (),
    frame_from: int | None = None,
    frame_to: int | None = None,
) -> list[ReadCluster]:
    reads_by_offset: dict[int, list[dict]] = defaultdict(list)
    for item in items:
        if item.get("type") != "rom-read":
            continue
        frame = int(item["frame"])
        if frame_from is not None and frame < frame_from:
            continue
        if frame_to is not None and frame > frame_to:
            continue
        offset = int(item["prgOffset"])
        cpu_address = item.get("cpuAddress")
        cpu_pc = item.get("cpuPc")
        if (
            cpu_address is not None
            and cpu_pc is not None
            and int(cpu_pc) <= int(cpu_address) <= int(cpu_pc) + 2
        ):
            # Mesen classifies instruction operand fetches as reads. They are
            # execution evidence, but they are not candidate text data.
            continue
        if any(start <= offset < end for start, end in excluded):
            continue
        reads_by_offset[offset].append(item)

    clusters: list[ReadCluster] = []
    current: list[int] = []
    for offset in sorted(reads_by_offset):
        if current and offset != current[-1] + 1:
            clusters.append(_make_cluster(current, reads_by_offset))
            current = []
        current.append(offset)
    if current:
        clusters.append(_make_cluster(current, reads_by_offset))
    return clusters


def _make_cluster(offsets: list[int], reads_by_offset: dict[int, list[dict]]) -> ReadCluster:
    reads = [item for offset in offsets for item in reads_by_offset[offset]]
    return ReadCluster(
        start=offsets[0],
        end_exclusive=offsets[-1] + 1,
        read_count=len(reads),
        frames=tuple(sorted({int(item["frame"]) for item in reads})),
        cpu_pcs=tuple(sorted({int(item["cpuPc"]) for item in reads})),
    )


def load_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("trace", type=Path)
    parser.add_argument("--min-bytes", type=int, default=2)
    parser.add_argument("--min-reads", type=int, default=2)
    parser.add_argument("--frame-from", type=int)
    parser.add_argument("--frame-to", type=int)
    args = parser.parse_args()

    clusters = cluster_reads(
        load_jsonl(args.trace),
        excluded=((0x0459, 0x049B),),
        frame_from=args.frame_from,
        frame_to=args.frame_to,
    )
    clusters = [
        cluster for cluster in clusters
        if cluster.end_exclusive - cluster.start >= args.min_bytes
        and cluster.read_count >= args.min_reads
    ]
    clusters.sort(key=lambda cluster: (-cluster.read_count, cluster.start))
    for cluster in clusters:
        print(json.dumps({
            "start": cluster.start,
            "endExclusive": cluster.end_exclusive,
            "length": cluster.end_exclusive - cluster.start,
            "readCount": cluster.read_count,
            "firstFrame": cluster.frames[0],
            "lastFrame": cluster.frames[-1],
            "cpuPcs": list(cluster.cpu_pcs),
        }))


if __name__ == "__main__":
    main()
