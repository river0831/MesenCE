#!/bin/zsh

set -eu

SCRIPT_DIR="${0:A:h}"
cd "$SCRIPT_DIR"

MESEN_PATH="bin/osx-arm64/Release/osx-arm64/publish/Mesen.app/Contents/MacOS/Mesen"
ROM_PATH="test_roms/Dragon Quest (Japan).nes"
PACK_PATH="Research/dragon-quest-jp/translation-pack.json"
TEMPLATE_PATH="Research/dragon-quest-jp/runtime/dialogue-glyph-provenance.lua"
COMPANION_PATH="Tools/NesTranslation/subtitle_companion_macos.py"
GENERATED_DIR="Research/dragon-quest-jp/generated"

require_file() {
  if [[ ! -f "$1" ]]; then
    print -u2 "无法启动：找不到 $1"
    print -u2 "请确认模拟器已编译，并且测试 ROM 位于预期位置。"
    read -r "?按回车键关闭窗口。"
    exit 1
  fi
}

require_file "$MESEN_PATH"
require_file "$ROM_PATH"
require_file "$PACK_PATH"
require_file "$TEMPLATE_PATH"
require_file "$COMPANION_PATH"

mkdir -p "$GENERATED_DIR"

print "正在启动 Dragon Quest 翻译测试……"
print "关闭模拟器后，本窗口会自动结束。"

python3 -m Tools.NesTranslation.dialogue_glyph_provenance \
  --mesen "$MESEN_PATH" \
  --template "$TEMPLATE_PATH" \
  --rom "$ROM_PATH" \
  --translation-pack "$PACK_PATH" \
  --external-subtitles \
  --subtitle-companion "$COMPANION_PATH" \
  --subtitle-debug-regions \
  --snapshot-trace "$GENERATED_DIR/visible-snapshots.jsonl" \
  --text-run-trace "$GENERATED_DIR/playtest-text-runs.jsonl" \
  --discovery-trace "$GENERATED_DIR/playtest-discoveries.jsonl"

