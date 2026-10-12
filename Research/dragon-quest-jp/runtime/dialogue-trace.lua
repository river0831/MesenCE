-- Bounded read-only capture for one Dragon Quest NPC dialogue.
-- Capture starts when the main command menu record is read. It records PRG
-- source-byte reads plus shared-dictionary expansion, the confirmed $0300
-- three-byte PPU update entries, and physical Nametable writes. No game memory
-- is modified.

local frame = 0
local captureStartFrame = nil
local captureFrames = 1200
local mainMenuStart = 0x8459
local mainMenuEnd = 0x849A
local previousInput = 0
local currentTokenAddress = nil
local currentTokenValue = nil

-- These PCs are the instruction after the relevant 6502 indirect read. Mesen
-- reports that next PC from inside a read callback.
local scriptFetchNextPc = 0xBD32 -- LDA ($99),Y at $BD30
local decodedFetchNextPc = 0xBEF4 -- LDA ($99),Y at $BEF2
local tokenDispatchPc = 0xBE6A -- CMP #$6D before dictionary dispatch
local dictionaryStart = 0x8858
local dictionaryEnd = 0x8B20
local ppuBufferWriterNextPc = 0xABBB
local glyphBitmapWriterNextPc = 0xC4BB

local function cpuPc()
  local state = emu.getCpuState(emu.cpuType.nes)
  return state.pc or state.PC or 0
end

local function isCapturing()
  return captureStartFrame ~= nil and frame - captureStartFrame <= captureFrames
end

local function startCapture(address)
  if captureStartFrame then return end
  captureStartFrame = frame
  print(string.format(
    "DQTRACE {\"type\":\"capture-start\",\"frame\":%d," ..
    "\"reason\":\"main-menu-read\",\"cpuAddress\":%d,\"cpuPc\":%d}",
    frame, address, cpuPc()
  ))
end

local function onMainMenuRead(address, value)
  if address >= mainMenuStart and address <= mainMenuEnd then startCapture(address) end
end

local function onCpuRead(address, value)
  if not isCapturing() then return end
  local pc = cpuPc()
  if pc == scriptFetchNextPc then
    -- ($99),Y first reads the two zero-page pointer bytes, then the effective
    -- address. Only the final bus read is record data.
    if address == 0x99 or address == 0x9A then return end
    print(string.format(
      "DQTRACE {\"type\":\"decoder-read\",\"frame\":%d," ..
      "\"cpuAddress\":%d,\"value\":%d,\"cpuPc\":%d," ..
      "\"storage\":\"%s\"}",
      frame, address, value, pc, address >= 0x8000 and "prg" or "ram"
    ))
  elseif pc == decodedFetchNextPc and
      address >= dictionaryStart and address <= dictionaryEnd then
    print(string.format(
      "DQTRACE {\"type\":\"dictionary-byte\",\"frame\":%d," ..
      "\"cpuAddress\":%d,\"value\":%d,\"cpuPc\":%d," ..
      "\"tokenAddress\":%s,\"tokenValue\":%s}",
      frame, address, value, pc,
      currentTokenAddress and tostring(currentTokenAddress) or "null",
      currentTokenValue and tostring(currentTokenValue) or "null"
    ))
  end
end

local function onTokenDispatch()
  if not isCapturing() then return end
  local state = emu.getCpuState(emu.cpuType.nes)
  local token = state.a or state.A or 0
  local pointer = emu.read(0x99, emu.memType.nesDebug) +
    emu.read(0x9A, emu.memType.nesDebug) * 256
  local inDictionary = pointer >= dictionaryStart and pointer <= dictionaryEnd

  if token >= 0x6D and not inDictionary then
    currentTokenAddress = pointer
    currentTokenValue = token
  end

  print(string.format(
    "DQTRACE {\"type\":\"text-token\",\"frame\":%d," ..
    "\"cpuAddress\":%d,\"value\":%d,\"cpuPc\":%d," ..
    "\"dictionarySource\":%s}",
    frame, pointer, token, tokenDispatchPc,
    inDictionary and "true" or "false"
  ))
end

local function onBufferWrite(address, value)
  if not isCapturing() or (address - 0x0300) % 3 ~= 2 then return end
  local pc = cpuPc()
  if pc == glyphBitmapWriterNextPc then
    print(string.format(
      "DQTRACE {\"type\":\"glyph-bitmap-byte\",\"frame\":%d," ..
      "\"ramAddress\":%d,\"value\":%d,\"cpuPc\":%d}",
      frame, address, value, pc
    ))
    return
  end
  if pc ~= ppuBufferWriterNextPc then return end
  local high = emu.read(address - 2, emu.memType.nesDebug)
  local low = emu.read(address - 1, emu.memType.nesDebug)
  print(string.format(
    "DQTRACE {\"type\":\"ppu-buffer-entry\",\"frame\":%d," ..
    "\"ramAddress\":%d,\"ppuAddress\":%d,\"value\":%d,\"cpuPc\":%d}",
    frame, address, high * 256 + low, value, pc
  ))
end

local function onNametableWrite(address, value)
  if not isCapturing() then return end
  print(string.format(
    "DQTRACE {\"type\":\"nametable-write\",\"frame\":%d," ..
    "\"address\":%d,\"value\":%d,\"cpuPc\":%d}",
    frame, address, value, cpuPc()
  ))
end

local function onEndFrame()
  frame = frame + 1
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
  onCpuRead, emu.callbackType.read, 0x0000, 0xFFFF,
  emu.cpuType.nes, emu.memType.nesMemory
)
emu.addMemoryCallback(
  onTokenDispatch, emu.callbackType.exec, tokenDispatchPc, tokenDispatchPc,
  emu.cpuType.nes, emu.memType.nesMemory
)
emu.addMemoryCallback(
  onBufferWrite, emu.callbackType.write, 0x0302, 0x03BF,
  emu.cpuType.nes, emu.memType.nesMemory
)
emu.addMemoryCallback(
  onNametableWrite, emu.callbackType.write, 0x0000, 0x07FF,
  emu.cpuType.nes, emu.memType.nesNametableRam
)

print(string.format(
  "DQTRACE_READY mode=dialogue captureFrames=%d scriptFetchNextPc=%d " ..
  "decodedFetchNextPc=%d tokenDispatchPc=%d",
  captureFrames, scriptFetchNextPc, decodedFetchNextPc, tokenDispatchPc
))
