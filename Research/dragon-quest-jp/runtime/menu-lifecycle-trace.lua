-- Bounded, read-only diagnostic capture for the Dragon Quest menu lifecycle.
--
-- Capture starts when the verified main-menu range is read. For the next 900
-- frames it records data reads from the surrounding ROM text/table region and
-- writes to NES internal RAM. This is discovery evidence: stable signals must
-- be confirmed before they are used by the production resolver.

local frame = 0
local captureStartFrame = nil
local captureFrames = 900
local mainMenuStart = 0x8459
local mainMenuEnd = 0x849A
local candidateStart = 0x8400
local candidateEnd = 0x8730
local captureFullRamWrites = false
local previousState = nil
local stateAddresses = {
  0x45, 0x47,
  0x94, 0x95, 0x96, 0x97, 0x98, 0x99, 0x9A, 0x9B, 0x9C, 0x9D,
  0xD0, 0xDA, 0xDF, 0xE0, 0xE5
}

local function cpuPc()
  local state = emu.getCpuState(emu.cpuType.nes)
  return state.pc or state.PC or 0
end

local function isCapturing()
  return captureStartFrame ~= nil and frame - captureStartFrame <= captureFrames
end

local function startCapture(address)
  if captureStartFrame == nil then
    captureStartFrame = frame
    print(string.format(
      "DQTRACE {\"type\":\"capture-start\",\"frame\":%d," ..
      "\"reason\":\"main-menu-read\",\"cpuAddress\":%d,\"cpuPc\":%d}",
      frame, address, cpuPc()
    ))
  end
end

local function onCandidateRead(address, value)
  if address >= mainMenuStart and address <= mainMenuEnd then
    startCapture(address)
  end
  if not isCapturing() then
    return
  end
  print(string.format(
    "DQTRACE {\"type\":\"rom-read\",\"frame\":%d,\"cpuAddress\":%d," ..
    "\"prgOffset\":%d,\"value\":%d,\"cpuPc\":%d}",
    frame, address, address - 0x8000, value, cpuPc()
  ))
end

local function onRamWrite(address, value)
  if not isCapturing() or not captureFullRamWrites then
    return
  end
  -- Full RAM writes are useful for first-pass discovery, but the stable state
  -- snapshots below are much smaller and are the preferred analysis input.
  print(string.format(
    "DQTRACE {\"type\":\"ram-write\",\"frame\":%d," ..
    "\"address\":%d,\"value\":%d,\"cpuPc\":%d}",
    frame, address, value, cpuPc()
  ))
end

local function stateSnapshot()
  local values = {}
  local parts = {}
  for index, address in ipairs(stateAddresses) do
    local value = emu.read(address, emu.memType.nesDebug)
    values[index] = value
    parts[index] = string.format("%d", value)
  end
  return table.concat(parts, ","), values
end

local function onEndFrame()
  frame = frame + 1
  if isCapturing() then
    local stateKey, values = stateSnapshot()
    if stateKey ~= previousState then
      previousState = stateKey
      print(string.format(
        "DQTRACE {\"type\":\"state\",\"frame\":%d," ..
        "\"menuMode\":%d,\"input\":%d,\"textLo\":%d,\"textHi\":%d," ..
        "\"values\":[%s]}",
        frame, values[1], values[2], values[8], values[9], stateKey
      ))
    end
  end
  if captureStartFrame ~= nil and frame - captureStartFrame == captureFrames + 1 then
    print(string.format(
      "DQTRACE {\"type\":\"capture-stop\",\"frame\":%d," ..
      "\"reason\":\"frame-limit\"}", frame
    ))
  end
end

emu.addEventCallback(onEndFrame, emu.eventType.endFrame)
emu.addMemoryCallback(
  onCandidateRead,
  emu.callbackType.read,
  candidateStart,
  candidateEnd,
  emu.cpuType.nes,
  emu.memType.nesMemory
)
emu.addMemoryCallback(
  onRamWrite,
  emu.callbackType.write,
  0x0000,
  0x07FF,
  emu.cpuType.nes,
  emu.memType.nesMemory
)

print(string.format(
  "DQTRACE_READY mode=menu-lifecycle captureFrames=%d candidateStart=%d candidateEnd=%d",
  captureFrames, candidateStart, candidateEnd
))
