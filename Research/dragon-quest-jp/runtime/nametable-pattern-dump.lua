-- Dump CIRAM tile ids together with the pattern bytes currently visible to PPU.
-- A host process consumes DQNT JSON. Read-only: no emulated memory is changed.

local frame = 0
local lastDigest = nil
local expectingSourceByte = false
local previousSourceByte = nil
local pendingModifier = nil
local chrWindowSetupPc = 0xC498
local chrWindowWriterPc = 0xC4BB
local scratchFirstAddress = 0x03B0
local ppuBufferWriterPc = 0xABBB
local pendingVoiceUploads = {}
local readyVoiceCaptures = {}

local function hexByte(value) return string.format("%02x", value) end

local function cpuPc()
  local state = emu.getCpuState(emu.cpuType.nes)
  return state.pc or state.PC or 0
end

local function patternHex(tile, patternBase)
  local bytes = {}
  for offset = 0, 15 do
    bytes[#bytes + 1] = hexByte(emu.read(
      patternBase + tile * 16 + offset, emu.memType.nesPpuMemory))
  end
  return table.concat(bytes)
end

local function onChrWindowSetup() expectingSourceByte = true end

local function onChrWindowWrite(address, value)
  if not expectingSourceByte or address ~= scratchFirstAddress then return end
  if cpuPc() ~= chrWindowWriterPc then return end
  expectingSourceByte = false
  if value == 0xF8 then
    pendingModifier = { baseSource = previousSourceByte, modifier = value, frame = frame }
    print(string.format(
      "DQMOD frame=%d sourceBase=$%02X modifier=$%02X",
      frame, previousSourceByte or 0xFF, value))
  elseif value < 0xF0 then
    previousSourceByte = value
  end
end

local function onBufferWrite(address, value)
  if (address - 0x0300) % 3 ~= 2 or cpuPc() ~= ppuBufferWriterPc then return end
  if not pendingModifier or frame - pendingModifier.frame > 2 then
    pendingModifier = nil
    return
  end
  local ppuAddress = emu.read(address - 2, emu.memType.nesDebug) * 256 +
    emu.read(address - 1, emu.memType.nesDebug)
  local state = emu.getState()
  local patternBase = state["ppu.control.backgroundPatternAddr"] or 0
  local baseSource = pendingModifier.baseSource or -1
  local basePattern = ""
  if baseSource >= 0 and baseSource <= 255 then
    basePattern = patternHex(baseSource, patternBase)
  end
  pendingVoiceUploads[ppuAddress % 0x800] = {
    frame = frame, sourceBase = baseSource,
    modifier = pendingModifier.modifier, ppuAddress = ppuAddress,
    ciramAddress = ppuAddress % 0x800, tileId = value,
    patternBase = patternBase, basePatternHex = basePattern,
  }
  pendingModifier = nil
end

local function onNametableWrite(address, value)
  local pending = pendingVoiceUploads[address]
  if pending and pending.tileId == value then
    readyVoiceCaptures[#readyVoiceCaptures + 1] = pending
    pendingVoiceUploads[address] = nil
  end
end

local function emitVoiceCapture(capture)
  local center = capture.ciramAddress
  local pageBase = math.floor(center / 0x400) * 0x400
  local within = center % 0x400
  local row = math.floor(within / 32)
  local column = within % 32
  local cells = {}
  for dy = -1, 1 do
    for dx = -1, 1 do
      local targetRow = row + dy
      local targetColumn = column + dx
      if targetRow >= 0 and targetRow < 30 and targetColumn >= 0 and targetColumn < 32 then
        local target = pageBase + targetRow * 32 + targetColumn
        local tile = emu.read(target, emu.memType.nesNametableRam)
        cells[#cells + 1] = string.format(
          "{\"dx\":%d,\"dy\":%d,\"ciramAddress\":%d," ..
          "\"tileId\":%d,\"patternHex\":\"%s\"}",
          dx, dy, target, tile, patternHex(tile, capture.patternBase))
      end
    end
  end
  print(string.format(
    "DQVOICE {\"frame\":%d,\"sourceBase\":%d,\"modifier\":%d," ..
    "\"ppuAddress\":%d,\"ciramAddress\":%d,\"tileId\":%d," ..
    "\"patternBase\":%d,\"patternHex\":\"%s\"," ..
    "\"basePatternHex\":\"%s\",\"neighborhood\":[%s]}",
    frame, capture.sourceBase, capture.modifier, capture.ppuAddress,
    capture.ciramAddress, capture.tileId, capture.patternBase,
    patternHex(capture.tileId, capture.patternBase),
    capture.basePatternHex, table.concat(cells, ",")))
end

local function snapshot()
  local state = emu.getState()
  local patternBase = state["ppu.control.backgroundPatternAddr"] or 0
  local tileParts = {}
  local used = {}
  local digest = 0
  for address = 0, 0x7FF do
    local value = emu.read(address, emu.memType.nesNametableRam)
    tileParts[#tileParts + 1] = hexByte(value)
    if (address % 0x400) < 0x3C0 then used[value] = true end
    digest = (digest + value * ((address % 251) + 1)) % 2147483647
  end
  if digest == lastDigest then return end
  lastDigest = digest

  local patternParts = {}
  for tile = 0, 255 do
    -- Export the complete active pattern table, not just the tiles currently
    -- visible.  The host can then compare a suspected voiced tile with its
    -- unvoiced base even when the base character is absent from this frame.
    local bytes = {}
    for offset = 0, 15 do
      bytes[#bytes + 1] = hexByte(emu.read(
        patternBase + tile * 16 + offset, emu.memType.nesPpuMemory))
    end
    patternParts[#patternParts + 1] = string.format(
      "\"%02X\":\"%s\"", tile, table.concat(bytes))
  end
  print(string.format(
    "DQNT {\"frame\":%d,\"patternBase\":%d,\"tilesHex\":\"%s\"," ..
    "\"patterns\":{%s}}", frame, patternBase, table.concat(tileParts),
    table.concat(patternParts, ",")))
end

local function onEndFrame()
  frame = frame + 1
  for _, capture in ipairs(readyVoiceCaptures) do emitVoiceCapture(capture) end
  readyVoiceCaptures = {}
  if frame >= 120 and frame % 30 == 0 then snapshot() end
end

emu.addEventCallback(onEndFrame, emu.eventType.endFrame)
emu.addMemoryCallback(onChrWindowSetup, emu.callbackType.exec,
  chrWindowSetupPc, chrWindowSetupPc, emu.cpuType.nes, emu.memType.nesMemory)
emu.addMemoryCallback(onChrWindowWrite, emu.callbackType.write,
  scratchFirstAddress, scratchFirstAddress, emu.cpuType.nes, emu.memType.nesMemory)
emu.addMemoryCallback(onBufferWrite, emu.callbackType.write, 0x0302, 0x03BF,
  emu.cpuType.nes, emu.memType.nesMemory)
emu.addMemoryCallback(onNametableWrite, emu.callbackType.write, 0x0000, 0x07FF,
  emu.cpuType.nes, emu.memType.nesNametableRam)
print("DQNT_READY")
