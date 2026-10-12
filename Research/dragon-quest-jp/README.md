# Dragon Quest translation proof of concept

This study is bound to one exact ROM and proves the path from a physical PRG
read to a translated display command. It does not modify or redistribute ROM
bytes outside the small reviewable text records in the database.

Validate the database against the local ROM:

```sh
python3 -m Tools.NesTranslation.validate \
  Research/dragon-quest-jp/database/game-database.json \
  "test_roms/Dragon Quest (Japan).nes"
```

Replay the synthetic menu trace:

```sh
python3 -m Tools.NesTranslation.replay \
  Research/dragon-quest-jp/database/game-database.json \
  Research/dragon-quest-jp/traces/main-menu-synthetic.jsonl
```

Run the live terminal proof of concept with the locally built MesenCE:

```sh
python3 -m Tools.NesTranslation.live \
  --mesen bin/osx-arm64/Release/osx-arm64/publish/Mesen.app/Contents/MacOS/Mesen \
  --script Research/dragon-quest-jp/runtime/menu-read-trace.lua \
  --rom "test_roms/Dragon Quest (Japan).nes" \
  --database Research/dragon-quest-jp/database/game-database.json
```

When the main command menu reads CPU `$8459-$849A` or the strength-detail
window reads CPU `$830F-$83F5`, Mesen emits `DQTRACE` events. The Python
resolver deduplicates the reads, switches between the database records, and
hides the active translation when the verified cancel input closes the menu
stack. PPU monitoring is not used.

## Database-driven visual overlay

The overlay launcher validates the exact ROM, loads every database record with
`presentation` metadata, injects that data into the generic Lua template, and
starts Mesen. The generated script exists only in a temporary directory. The
template contains no Dragon Quest record IDs, addresses, translations, or
coordinates.

```sh
python3 -m Tools.NesTranslation.overlay \
  --mesen bin/osx-arm64/Release/osx-arm64/publish/Mesen.app/Contents/MacOS/Mesen \
  --template Research/dragon-quest-jp/runtime/database-overlay.lua \
  --rom "test_roms/Dragon Quest (Japan).nes" \
  --database Research/dragon-quest-jp/database/game-database.json
```

The main command menu and strength-detail window both use this path. Static
labels are covered and redrawn while the game's dynamic numbers and equipment
values remain visible. No ROM, emulated RAM, or emulator-core modification is
used.

## Capture menu lifecycle evidence

The lifecycle capture is a bounded diagnostic run. It starts at the first
verified main-menu read, then records nearby ROM data reads and internal-RAM
writes for 900 frames. Generated traces are ignored by Git.

```sh
python3 -m Tools.NesTranslation.capture \
  --mesen bin/osx-arm64/Release/osx-arm64/publish/Mesen.app/Contents/MacOS/Mesen \
  --script Research/dragon-quest-jp/runtime/menu-lifecycle-trace.lua \
  --rom "test_roms/Dragon Quest (Japan).nes" \
  --output Research/dragon-quest-jp/generated/menu-lifecycle.jsonl
```

During the bounded capture, open the main menu, enter the item menu, return to
the main menu, and close it. This trace is discovery evidence only; RAM writes
must not be promoted to runtime locators until repeated runs are consistent.

For child-menu discovery, use `runtime/child-menu-trace.lua` with the same
capture command. It observes data reads across the complete PRG mapping while
deduplicating reads per frame and CPU PC. Summarize the result with:

```sh
python3 -m Tools.NesTranslation.analyze_reads \
  Research/dragon-quest-jp/generated/item-menu.jsonl
```

## Lightweight Nametable provenance prototype

This read-only diagnostic keeps a shadow copy of physical Nametable RAM. A
database text read opens a short source context, and nearby Nametable writes
inherit that record ID. Later untagged writes replace the metadata, so a record
group naturally reaches zero cells when its tiles are cleared or overwritten.

```sh
python3 -m Tools.NesTranslation.provenance \
  --mesen bin/osx-arm64/Release/osx-arm64/publish/Mesen.app/Contents/MacOS/Mesen \
  --template Research/dragon-quest-jp/runtime/nametable-provenance.lua \
  --rom "test_roms/Dragon Quest (Japan).nes" \
  --database Research/dragon-quest-jp/database/game-database.json
```

`DQPROV source` identifies the active database record. `DQPROV group` reports
how many physical Nametable cells currently carry that tag and their bounds.
When the database declares `runtime.ppuUpdateBuffer`, tags are attached only to
the configured tile-value slots and follow their NMI reads into physical
Nametable writes. The frame TTL remains only on the earlier ROM-read-to-buffer-
production step; it is no longer used to claim arbitrary Nametable writes.

Trace the intermediate RAM buffer with the same launcher and the buffer
diagnostic template:

```sh
python3 -m Tools.NesTranslation.provenance \
  --mesen bin/osx-arm64/Release/osx-arm64/publish/Mesen.app/Contents/MacOS/Mesen \
  --template Research/dragon-quest-jp/runtime/ppu-buffer-provenance.lua \
  --rom "test_roms/Dragon Quest (Japan).nes" \
  --database Research/dragon-quest-jp/database/game-database.json
```

This correlates tagged RAM writes with same-value RAM reads immediately before
a physical Nametable write. It emits one `DQBUFFER buffer-summary` per record
when the script exits. It is a discovery tool; confirmed buffer structure must
still be checked against the 6502 code before becoming runtime configuration.

## Provenance-driven visual overlay

The next adapter uses sourced Nametable groups, not controller input, to drive
the existing translated labels:

```sh
python3 -m Tools.NesTranslation.provenance \
  --mesen bin/osx-arm64/Release/osx-arm64/publish/Mesen.app/Contents/MacOS/Mesen \
  --template Research/dragon-quest-jp/runtime/provenance-overlay.lua \
  --rom "test_roms/Dragon Quest (Japan).nes" \
  --database Research/dragon-quest-jp/database/game-database.json
```

A newly sourced record takes focus immediately, and labels are drawn after its
group remains stable for two frames. Bulk untagged writes clear a group and
hide its overlay. Small per-frame changes are treated as cursor or dynamic-
field updates so moving the menu cursor does not flicker the translation.

## Capture one NPC dialogue

Stand next to a repeatable NPC before launching this bounded capture. Open the
main command menu, choose `はなす`, advance the complete dialogue, and close
Mesen. The trace combines decoder reads, token dispatch at CPU `$BE6A`, shared-
dictionary expansion, decoded `$0300` PPU-buffer entries, and physical
Nametable writes without modifying emulated memory. The hooks are restricted
to confirmed decoder sites so instruction fetches and unrelated ROM traffic
are not included.

```sh
python3 -m Tools.NesTranslation.capture \
  --mesen bin/osx-arm64/Release/osx-arm64/publish/Mesen.app/Contents/MacOS/Mesen \
  --script Research/dragon-quest-jp/runtime/dialogue-trace.lua \
  --rom "test_roms/Dragon Quest (Japan).nes" \
  --output Research/dragon-quest-jp/generated/dialogue.jsonl
```

The dialogue trace established that this ROM also stores compressed text in
CHR ROM. Export lossless `$FC`-terminated CHR candidates with:

```sh
python3 -m Tools.NesTranslation.chr_records \
  --rom "test_roms/Dragon Quest (Japan).nes" \
  --terminator fc \
  --minimum-length 2 \
  --maximum-length 256 \
  --output Research/dragon-quest-jp/generated/chr-fc-records.json
```

This is deliberately a broad candidate export. It preserves every byte and
physical CHR/file offset, but does not claim that all candidates are text.
Runtime evidence cross-validates the first NPC-dialogue candidate at CHR
`$3397-$33C1`.

Expand that candidate through the PRG shared dictionary while retaining every
source offset and control byte:

```sh
python3 -m Tools.NesTranslation.dictionary_codec \
  --rom "test_roms/Dragon Quest (Japan).nes" \
  --chr-start 0x3397 \
  --chr-end 0x33c1 \
  --dictionary-start 0x858 \
  --dictionary-end 0xb21 \
  --dictionary-terminator fa \
  --token-base 6d \
  --modifier f8 \
  --control-minimum f0 \
  --output Research/dragon-quest-jp/generated/dialogue-3397-expanded.json
```

Render an evidence-bearing review without hiding unknown bytes:

```sh
python3 -m Tools.NesTranslation.text_review \
  --expanded Research/dragon-quest-jp/generated/dialogue-3397-expanded.json \
  --character-map Research/dragon-quest-jp/database/character-map.json \
  --confidence runtime-confirmed \
  --output Research/dragon-quest-jp/output/dialogue-3397-review.md
```

Build a lossless catalog for every bounded `$FC`-terminated CHR record, expand
dictionary tokens, rank candidates, and emit a combined review:

```sh
python3 -m Tools.NesTranslation.dialogue_catalog \
  --rom "test_roms/Dragon Quest (Japan).nes" \
  --character-map Research/dragon-quest-jp/database/character-map.json \
  --dictionary-start 0x858 \
  --dictionary-end 0xb21 \
  --dictionary-terminator fa \
  --token-base 6d \
  --record-terminator fc \
  --modifier f8 \
  --control-minimum f0 \
  --minimum-length 2 \
  --maximum-length 256 \
  --catalog-output Research/dragon-quest-jp/generated/dialogue-catalog.json \
  --review-output Research/dragon-quest-jp/generated/dialogue-candidate-review.md \
  --review-likelihood high \
  --review-likelihood medium
```

The JSON catalog includes low-likelihood records as well: classification never
discards source or expanded bytes. Scores are review ordering only. CHR bitmap
data can coincidentally resemble dictionary tokens, so even a `high` record has
confidence `static-candidate` until runtime reads or another independent source
cross-validates it.

Match captured overlapping CHR staging windows back to stable catalog IDs:

```sh
python3 -m Tools.NesTranslation.runtime_catalog_match \
  --trace Research/dragon-quest-jp/generated/dialogue-visual-validation.jsonl \
  --catalog Research/dragon-quest-jp/generated/dialogue-catalog.json \
  --output Research/dragon-quest-jp/generated/dialogue-runtime-matches.json
```

The matcher consumes only the first byte of each `$03B0-$03B7` overlapping
window, requires a stable selector and monotonic PPU-source progression, and
then performs an exact lossless match against catalog source bytes. It does not
use decoded Japanese text to decide identity.

For a focused multi-dialogue validation capture, use
`runtime/dialogue-catalog-trace.lua`. It starts after the main command menu is
read, runs for 3600 frames, and omits Nametable and PPU-buffer logging. Open the
menu once, speak to two or more NPCs, finish their dialogue, then close Mesen.

Merge one or more exact-match reports back into a generated validated catalog:

```sh
python3 -m Tools.NesTranslation.catalog_validation \
  --catalog Research/dragon-quest-jp/generated/dialogue-catalog.json \
  --matches Research/dragon-quest-jp/generated/dialogue-runtime-matches.json \
  --matches Research/dragon-quest-jp/generated/dialogue-catalog-validation-matches.json \
  --matches Research/dragon-quest-jp/generated/dialogue-catalog-validation-2-matches.json \
  --output Research/dragon-quest-jp/generated/dialogue-catalog-validated.json
```

This preserves the static ranking while promoting exact runtime hits, recording
each observation and keeping occurrence count separate from distinct record
count.

Run the first CHR-source-driven translated dialogue overlay with:

```sh
python3 -m Tools.NesTranslation.dialogue_overlay \
  --mesen bin/osx-arm64/Release/osx-arm64/publish/Mesen.app/Contents/MacOS/Mesen \
  --template Research/dragon-quest-jp/runtime/dialogue-overlay.lua \
  --rom "test_roms/Dragon Quest (Japan).nes" \
  --game-database Research/dragon-quest-jp/database/game-database.json \
  --catalog Research/dragon-quest-jp/generated/dialogue-catalog-validated.json \
  --translations Research/dragon-quest-jp/database/dialogue-translations.json
```

The committed translation specification contains only stable IDs, reviewed
source/translation text, layout, and exact-ROM runtime configuration. Raw CHR
record bytes are injected from the locally generated catalog into a temporary
Lua script and are not duplicated in the tracked translation database.
