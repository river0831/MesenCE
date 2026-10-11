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
restores the main-menu translation when the detail window is cancelled. PPU
monitoring is not used.

## Strength-menu visual overlay prototype

`runtime/strength-overlay.lua` covers only the ten static labels in the
runtime-confirmed strength window. The original numeric and equipment values
remain visible. It uses Mesen's console-screen drawing surface and does not
modify ROM, emulated RAM, or the emulator core. The initial label positions are
visual-provisional until checked at native 256x240 coordinates.

```sh
bin/osx-arm64/Release/osx-arm64/publish/Mesen.app/Contents/MacOS/Mesen \
  --enableStdout --doNotSaveSettings \
  Research/dragon-quest-jp/runtime/strength-overlay.lua \
  "test_roms/Dragon Quest (Japan).nes"
```

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
