-- Lightweight read-only capture for matching displayed dialogue to the static
-- CHR catalog. Capture starts on the main command menu and records only the
-- mapper selector plus overlapping CHR staging windows. No memory is modified.

local frame = 0
local captureStartFrame = nil
local captureFrames = 3600
local mainMenuStart = 0x8459
local mainMenuEnd = 0x849A
local chrWindowWriterNextPc = 0xC4BB
local chrStreamSelectorPc = 0xC433
local chrWindowSetupPc = 0xC498
local currentChrStreamSelector = nil

local function cpuPc()
  local state = emu.getCpuState(emu.cpuType.nes)
  return state.pc or state.PC or 0
end

local function isCapturing()
  return captureStartFrame ~= nil and frame - captureStartFrame <= captureFrames
end

local function onMainMenuRead(address, value)
  if captureStartFrame or address < mainMenuStart or address > mainMenuEnd then return end
  captureStartFrame = frame
  print(string.format(
    "DQTRACE {\"type\":\"capture-start\",\"frame\":%d," ..
    "\"reason\":\"main-menu-read\",\"cpuAddress\":%d,\"cpuPc\":%d}",
    frame, address, cpuPc()
  ))
end

local function onChrStreamSelector()
  if not isCapturing() then return end
  currentChrStreamSelector = emu.read(0x3C, emu.memType.nesDebug) +
    emu.read(0x3D, emu.memType.nesDebug) * 256
  print(string.format(
    "DQTRACE {\"type\":\"chr-stream-selector\",\"frame\":%d," ..
    "\"value\":%d,\"cpuPc\":%d}",
    frame, currentChrStreamSelector, chrStreamSelectorPc
  ))
end

local function onChrWindowSetup()
  if not isCapturing() then return end
  local sourcePointer = emu.read(0x99, emu.memType.nesDebug) +
    emu.read(0x9A, emu.memType.nesDebug) * 256
  local ppuAddress = emu.read(0xDC, emu.memType.nesDebug) +
    emu.read(0xDD, emu.memType.nesDebug) * 256
  print(string.format(
    "DQTRACE {\"type\":\"chr-text-window\",\"frame\":%d," ..
    "\"selector\":%s,\"sourcePointer\":%d,\"ppuAddress\":%d," ..
    "\"cpuPc\":%d}",
    frame,
    currentChrStreamSelector and tostring(currentChrStreamSelector) or "null",
    sourcePointer, ppuAddress, chrWindowSetupPc
  ))
end

local function onChrWindowWrite(address, value)
  if not isCapturing() or cpuPc() ~= chrWindowWriterNextPc then return end
  print(string.format(
    "DQTRACE {\"type\":\"chr-text-byte\",\"frame\":%d," ..
    "\"ramAddress\":%d,\"value\":%d,\"cpuPc\":%d}",
    frame, address, value, chrWindowWriterNextPc
  ))
end

local function onEndFrame()
  frame = frame + 1
  if captureStartFrame and frame - captureStartFrame == captureFrames + 1 then
    print(string.format(
      "DQTRACE {\"type\":\"capture-stop\",\"frame\":%d," ..
      "\"reason\":\"frame-limit\"}", frame
    ))
  end
end

emu.addEventCallback(onEndFrame, emu.eventType.endFrame)
emu.addMemoryCallback(
  onMainMenuRead, emu.callbackType.read, mainMenuStart, mainMenuEnd,
  emu.cpuType.nes, emu.memType.nesMemory
)
emu.addMemoryCallback(
  onChrStreamSelector, emu.callbackType.exec,
  chrStreamSelectorPc, chrStreamSelectorPc,
  emu.cpuType.nes, emu.memType.nesMemory
)
emu.addMemoryCallback(
  onChrWindowSetup, emu.callbackType.exec, chrWindowSetupPc, chrWindowSetupPc,
  emu.cpuType.nes, emu.memType.nesMemory
)
emu.addMemoryCallback(
  onChrWindowWrite, emu.callbackType.write, 0x03B0, 0x03B7,
  emu.cpuType.nes, emu.memType.nesMemory
)

print(string.format(
  "DQTRACE_READY mode=dialogue-catalog captureFrames=%d", captureFrames
))
