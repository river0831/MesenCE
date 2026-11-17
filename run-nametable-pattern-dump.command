#!/bin/zsh

set -eu
PROJECT_DIR="${0:A:h}"
cd "$PROJECT_DIR"

python3 -m Tools.NesTranslation.dialogue_glyph_provenance \
  --mesen "bin/osx-arm64/Release/osx-arm64/publish/Mesen.app/Contents/MacOS/Mesen" \
  --rom "test_roms/Dragon Quest (Japan).nes" \
  --template "Research/dragon-quest-jp/runtime/dialogue-glyph-provenance.lua" \
  --translation-pack "Research/dragon-quest-jp/translation-pack.json" \
  --snapshot-trace "Research/dragon-quest-jp/generated/nametable-pattern-dump/provenance-snapshots.jsonl" \
  --voicing-capture-dir "Research/dragon-quest-jp/generated/nametable-pattern-dump"
