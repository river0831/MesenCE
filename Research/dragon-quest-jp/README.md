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
  --translations Research/dragon-quest-jp/database/dialogue-translations.json \
  --font-source Core/Shared/Video/DrawStringCommand.cpp
```

The committed translation specification contains only stable IDs, reviewed
source/translation text, layout, and exact-ROM runtime configuration. Raw CHR
record bytes are injected from the locally generated catalog into a temporary
Lua script and are not duplicated in the tracked translation database.
`--font-source` validates every presentation character against Mesen's built-in
HUD glyph table so unsupported Chinese characters fail generation instead of
silently disappearing. Canonical translations remain simplified Chinese;
`pages[].lines` may use font-compatible traditional presentation glyphs.

Generate and run the diagnostic logical-glyph provenance adapter with:

```sh
python3 -m Tools.NesTranslation.dialogue_glyph_provenance \
  --mesen bin/osx-arm64/Release/osx-arm64/publish/Mesen.app/Contents/MacOS/Mesen \
  --template Research/dragon-quest-jp/runtime/dialogue-glyph-provenance.lua \
  --rom "test_roms/Dragon Quest (Japan).nes" \
  --game-database Research/dragon-quest-jp/database/game-database.json \
  --catalog Research/dragon-quest-jp/generated/dialogue-catalog-validated.json \
  --translations Research/dragon-quest-jp/database/dialogue-translations.json \
  --character-map Research/dragon-quest-jp/database/character-map.json
```

`DQGLYPH visible-ranges` events report the logical source-glyph interval owned
by each currently tagged Nametable row. Dakuten and other modifiers do not
advance the logical index. Controls and unknown bytes remain in the catalog but
are not guessed to be visible glyphs. This is a read-only diagnostic: it does
not draw translations or modify ROM/emulated memory.

Add `--display-segments` and
`--font-source Core/Shared/Video/DrawStringCommand.cpp` to turn on the
experimental range-driven presentation. Each reviewed `segments[]` entry maps
an exact logical source interval to one or more translated lines. The adapter
uses the newest visible logical glyph as its segment anchor, hides presentation
until the first segment is identified, and atomically switches only when the
newest glyph crosses a reviewed segment boundary. The current segment remains
visible through ordinary glyph writes and short empty intervals during scroll;
a sustained empty interval resets the record so it can be recognized again.
Controller input is not observed.

On macOS, run the same provenance adapter with a separate native subtitle
window instead of drawing over the emulated frame:

```sh
python3 -m Tools.NesTranslation.dialogue_glyph_provenance \
  --mesen bin/osx-arm64/Release/osx-arm64/publish/Mesen.app/Contents/MacOS/Mesen \
  --template Research/dragon-quest-jp/runtime/dialogue-glyph-provenance.lua \
  --rom "test_roms/Dragon Quest (Japan).nes" \
  --game-database Research/dragon-quest-jp/database/game-database.json \
  --catalog Research/dragon-quest-jp/generated/dialogue-catalog-validated.json \
  --translations Research/dragon-quest-jp/database/dialogue-translations.json \
  --character-map Research/dragon-quest-jp/database/character-map.json \
  --external-subtitles \
  --subtitle-companion Tools/NesTranslation/subtitle_companion_macos.py \
  --snapshot-trace Research/dragon-quest-jp/generated/visible-snapshots.jsonl
```

`--snapshot-trace` is optional. It records exactly the renderer-independent
snapshots sent to the companion, including frame numbers and unit deltas. It
does not contain ROM bytes. The trace can also be recorded without
`--external-subtitles` when only a diagnostic capture is needed.

Replay a capture without starting Mesen or loading the ROM:

```sh
python3 -m Tools.NesTranslation.snapshot_replay \
  --trace Research/dragon-quest-jp/generated/visible-snapshots.jsonl \
  --subtitle-companion Tools/NesTranslation/subtitle_companion_macos.py \
  --speed 1
```

`--speed 2` replays at twice the recorded frame rate. `--fps` defaults to 60
and can be adjusted for another system or capture convention.

The runtime event router is renderer-independent. The current companion is a
small AppKit prototype which accepts ordinary JSON subtitle state over stdin;
it neither embeds game-specific logic nor changes the emulator frame. This
also removes the Mesen HUD bitmap-font restriction from translated text.

The same external window also accepts short UI text. Known
menu records travel through the existing exact `$0300` PPU-buffer-to-Nametable
path. Their database labels are normalized from the 256x240 NES coordinate
space and drawn at corresponding positions in the companion. The router emits
one composed `scene`: every currently sourced menu record and every qualifying
dialogue interval can be rendered at the same time.

External dialogue selection uses visible coverage rather than the greatest
glyph index alone. Each runtime snapshot counts sourced Nametable cells inside
every reviewed alignment interval. A translation is present exactly while at
least 25% of that source interval is currently tagged in the shadow Nametable;
there is no controller-triggered lifetime or remembered subtitle fallback.
Multiple genuinely visible source sentences can produce multiple translated
lines without exposing a later sentence merely because both previously shared
one coarse record range. Rewriting the same tile value to the same cell keeps
its provenance, since such a redraw does not change the visible state.

Vertical dialogue scrolling is treated as provenance movement rather than new
text. Unattributed write batches vote for a 32-tile row displacement; a match
requires at least three agreeing tiles and one logical glyph may occupy only
one current cell. Short UI labels are likewise tracked individually through
their database `clear` rectangles, so a higher window hides only the labels it
actually covers instead of keeping or removing an entire menu record.

The macOS companion is a `256x240` logical translation mirror, initially shown
at `3x` size. Label and dialogue rectangles use PPU pixel coordinates and are
scaled with the window. Label ownership is resolved in screen space by
combining each logical Nametable address with the current NES temporary VRAM
address and fine-X scroll, rather than confusing physical Nametable offsets
with visible coordinates.

The renderer receives a `visible-translation-snapshot` rather than separate
menu and subtitle commands. Every current unit has the same fields: stable
unit/record IDs, translated text, PPU bounds, visible and total cell/glyph
counts, coverage ratio, and presentation font size. This snapshot is a direct
projection of tracked PPU state; it does not identify a game scene or retain a
previous subtitle.

Before projection, database menu labels and reviewed dialogue segments are
normalized into the same internal `TextUnit` read model. This adds no game
scene semantics: a unit only describes translated text, PPU-space bounds,
coverage size, and an optional source interval. The proven Lua collectors
remain separate input adapters.

The router's live state is a single `unitId -> visibleCount` map. Each input
adapter replaces only the units supported by its latest Nametable snapshot;
units absent from that snapshot are removed. Menu and dialogue lifetimes are
therefore derived from current PPU provenance, not controller actions or a
remembered presentation mode.

Every emitted snapshot also includes a diagnostic `delta` with stable unit IDs
that appeared, changed, or disappeared since the previous snapshot. Renderers
do not need this field; it exists so visibility and overlap bugs can be traced
without inferring lifecycle changes from screenshots.
