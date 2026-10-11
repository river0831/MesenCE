-- Read-only discovery trace for locating data used by a Dragon Quest child menu.
--
-- The verified main-menu read starts a bounded capture. Data reads from the
-- complete 32 KiB PRG window are deduplicated per frame and CPU PC. Instruction
-- fetches use Mesen's execute callback and are therefore not included here.

local frame = 0
local captureStartFrame = nil
local captureFrames = 900
local mainMenuStart = 0x8459
local mainMenuEnd = 0x849A
local seenReads = {}
local previousInput = 0
local observedRecords = {}

local records = {
  { id = "status-summary", startAddress = 0x82D3, endAddress = 0x830E },
  { id = "strength-detail", startAddress = 0x830F, endAddress = 0x839D },
}

local function cpuPc()
  local state = emu.getCpuState(emu.cpuType.nes)
  return state.pc or state.PC or 0
end

local function isCapturing()
  return captureStartFrame ~= nil and frame - captureStartFrame <= captureFrames
end

local function onPrgRead(address, value)
  if captureStartFrame == nil and address >= mainMenuStart and address <= mainMenuEnd then
    captureStartFrame = frame
    print(string.format(
      "DQTRACE {\"type\":\"capture-start\",\"frame\":%d," ..
      "\"reason\":\"main-menu-read\",\"cpuAddress\":%d,\"cpuPc\":%d}",
      frame, address, cpuPc()
    ))
  end
  if not isCapturing() then
    return
  end

  for _, record in ipairs(records) do
    if not observedRecords[record.id]
        and address >= record.startAddress
        and address <= record.endAddress then
      observedRecords[record.id] = true
      print(string.format(
        "DQTRACE {\"type\":\"record-hit\",\"frame\":%d," ..
        "\"recordId\":\"%s\",\"cpuAddress\":%d,\"prgOffset\":%d}",
        frame, record.id, address, address - 0x8000
      ))
    end
  end

  local pc = cpuPc()
  local key = string.format("%d:%d", address, pc)
  if seenReads[key] then
    return
  end
  seenReads[key] = true
  print(string.format(
    "DQTRACE {\"type\":\"rom-read\",\"frame\":%d,\"cpuAddress\":%d," ..
    "\"prgOffset\":%d,\"value\":%d,\"cpuPc\":%d}",
    frame, address, address - 0x8000, value, pc
  ))
end

local function onEndFrame()
  frame = frame + 1
  seenReads = {}
  if isCapturing() then
    local input = emu.read(0x47, emu.memType.nesDebug)
    if input ~= 0 and input ~= previousInput then
      print(string.format(
        "DQTRACE {\"type\":\"input\",\"frame\":%d,\"buttons\":%d}",
        frame, input
      ))
    end
    previousInput = input
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
  onPrgRead,
  emu.callbackType.read,
  0x8000,
  0xFFFF,
  emu.cpuType.nes,
  emu.memType.nesMemory
)

print(string.format(
  "DQTRACE_READY mode=child-menu captureFrames=%d prgStart=%d prgEnd=%d",
  captureFrames, 0x8000, 0xFFFF
))
