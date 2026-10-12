-- Lightweight dialogue glyph -> Nametable provenance diagnostic.
-- The generated configuration contains only reviewed catalog metadata. This
-- script observes the existing PPU update path and never modifies game state.

-- __NES_TRANSLATION_GLYPH_PROVENANCE_CONFIG__

local ppuBufferWriterPc = 0xABBB
local frame = 0
local expectingFirstByte = false
local stream = {}
local maxPrefixLength = 0
local activeRecord = nil
local nextGlyph = 1
local pendingBeforeMatch = {}
local pendingUploads = {}
local cells = {}
local changed = false
local lastChangedFrame = -1
local stableFrames = 4
local selectedSegment = nil
local foreground = 0xFFFFFF
local background = 0x000000

for _, record in ipairs(records) do
  maxPrefixLength = math.max(maxPrefixLength, #record.matchPrefix)
end

local function cpuPc()
  local state = emu.getCpuState(emu.cpuType.nes)
  return state.pc or state.PC or 0
end

local function jsonString(value) return string.format("%q", value) end

local function prefixMatches(prefix)
  if #stream < #prefix then return false end
  for index = 1, #prefix do
    if stream[index] ~= prefix[index] then return false end
  end
  return true
end

local function alignCandidate(candidate, alreadyUploaded)
  if not activeRecord then return end
  local glyph = activeRecord.glyphs[nextGlyph]
  if not glyph or candidate.value ~= glyph.value then return end
  local address = candidate.ppuAddress % 0x400
  if address < visibilityStart or address >= visibilityEndExclusive then return end
  local tag = {
    recordId = activeRecord.id,
    glyphIndex = glyph.index,
    sourceOffset = glyph.sourceOffset,
    expandedIndex = glyph.expandedIndex,
    value = candidate.value,
  }
  if alreadyUploaded then
    cells[address] = tag
    changed = true
  else
    pendingUploads[address] = tag
  end
  nextGlyph = nextGlyph + 1
end

local function activateRecord(record)
  activeRecord = record
  nextGlyph = 1
  for _, candidate in ipairs(pendingBeforeMatch) do alignCandidate(candidate, true) end
  pendingBeforeMatch = {}
  print(string.format(
    "DQGLYPH {\"type\":\"record\",\"frame\":%d,\"recordId\":%s}",
    frame, jsonString(record.id)
  ))
end

local function consumeSourceByte(value)
  table.insert(stream, value)
  if #stream > maxPrefixLength or activeRecord then return end
  for _, record in ipairs(records) do
    if prefixMatches(record.matchPrefix) then activateRecord(record); return end
  end
end

local function onChrStreamSelector()
  stream = {}
  pendingBeforeMatch = {}
end

local function onChrWindowSetup() expectingFirstByte = true end

local function onChrWindowWrite(address, value)
  if not expectingFirstByte or address ~= scratchFirstAddress then return end
  if cpuPc() ~= chrWindowWriterPc then return end
  expectingFirstByte = false
  consumeSourceByte(value)
end

local function onBufferWrite(address, value)
  if (address - 0x0300) % 3 ~= 2 or cpuPc() ~= ppuBufferWriterPc then return end
  local candidate = {
    ppuAddress = emu.read(address - 2, emu.memType.nesDebug) * 256 +
      emu.read(address - 1, emu.memType.nesDebug),
    value = value,
  }
  if activeRecord then
    alignCandidate(candidate, false)
  else
    table.insert(pendingBeforeMatch, candidate)
  end
end

local function onNametableWrite(address, value)
  -- A later game write owns the cell. Only the exact queued destination/value
  -- inherits a tag; every unrelated write clears old provenance.
  local pending = pendingUploads[address]
  if pending and pending.value == value then
    cells[address] = pending
    pendingUploads[address] = nil
    changed = true
  elseif cells[address] then
    cells[address] = nil
    changed = true
  end
end

local function emitVisibleRanges()
  local rows = {}
  for address, cell in pairs(cells) do
    local row = math.floor((address % 0x400) / 32)
    local key = cell.recordId .. ":" .. tostring(row)
    local item = rows[key]
    if not item then
      item = { recordId = cell.recordId, row = row, start = cell.glyphIndex,
        finish = cell.glyphIndex, count = 0 }
      rows[key] = item
    end
    item.start = math.min(item.start, cell.glyphIndex)
    item.finish = math.max(item.finish, cell.glyphIndex)
    item.count = item.count + 1
  end
  local parts = {}
  for _, item in pairs(rows) do
    table.insert(parts, string.format(
      "{\"recordId\":%s,\"row\":%d,\"start\":%d," ..
      "\"endExclusive\":%d,\"cellCount\":%d}",
      jsonString(item.recordId), item.row, item.start, item.finish + 1, item.count
    ))
  end
  print(string.format(
    "DQGLYPH {\"type\":\"visible-ranges\",\"frame\":%d,\"rows\":[%s]}",
    frame, table.concat(parts, ",")
  ))
end

local function chooseSegment()
  local newest = -1
  local record = nil
  for _, cell in pairs(cells) do
    if cell.glyphIndex > newest then
      newest = cell.glyphIndex
      record = activeRecord
    end
  end
  if not record then return nil end
  for _, segment in ipairs(record.segments) do
    if newest >= segment.sourceStart and newest < segment.sourceEndExclusive then
      return segment
    end
  end
  return nil
end

local function drawSelectedSegment()
  if not displaySegments or not activeRecord or not selectedSegment then return end
  emu.selectDrawSurface(emu.drawSurface.consoleScreen)
  emu.drawRectangle(activeRecord.x, activeRecord.y, activeRecord.width,
    activeRecord.height, background, true, 1)
  for index, line in ipairs(selectedSegment.lines) do
    emu.drawString(activeRecord.x + 4,
      activeRecord.y + 4 + (index - 1) * activeRecord.lineHeight,
      line, foreground, background, 0, 1)
  end
end

local function onEndFrame()
  if changed then
    emitVisibleRanges()
    selectedSegment = nil
    lastChangedFrame = frame
    changed = false
  elseif displaySegments and not selectedSegment
      and frame - lastChangedFrame >= stableFrames then
    selectedSegment = chooseSegment()
    if selectedSegment then
      print(string.format(
        "DQGLYPH {\"type\":\"segment\",\"frame\":%d," ..
        "\"recordId\":%s,\"sourceStart\":%d,\"sourceEndExclusive\":%d}",
        frame, jsonString(activeRecord.id), selectedSegment.sourceStart,
        selectedSegment.sourceEndExclusive
      ))
    end
  end
  drawSelectedSegment()
  frame = frame + 1
end

emu.addMemoryCallback(onChrStreamSelector, emu.callbackType.exec,
  chrStreamSelectorPc, chrStreamSelectorPc, emu.cpuType.nes, emu.memType.nesMemory)
emu.addMemoryCallback(onChrWindowSetup, emu.callbackType.exec,
  chrWindowSetupPc, chrWindowSetupPc, emu.cpuType.nes, emu.memType.nesMemory)
emu.addMemoryCallback(onChrWindowWrite, emu.callbackType.write,
  scratchFirstAddress, scratchFirstAddress, emu.cpuType.nes, emu.memType.nesMemory)
emu.addMemoryCallback(onBufferWrite, emu.callbackType.write, 0x0302, 0x03BF,
  emu.cpuType.nes, emu.memType.nesMemory)
emu.addMemoryCallback(onNametableWrite, emu.callbackType.write, 0x0000, 0x07FF,
  emu.cpuType.nes, emu.memType.nesNametableRam)
emu.addEventCallback(onEndFrame, emu.eventType.endFrame)

print(string.format("DQGLYPH_READY records=%d", #records))
