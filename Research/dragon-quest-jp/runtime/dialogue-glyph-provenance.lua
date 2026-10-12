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
local previousCells = {}
local untaggedWrites = {}
local changed = false
local selectedSegment = nil
local emptySinceFrame = nil
local emptyGraceFrames = 20
local foreground = 0xFFFFFF
local background = 0x000000
local layoutSource = nil
local layoutSourceExpires = -1
local layoutPending = {}
local layoutCells = {}
local layoutDirty = {}
local layoutSourceTtlFrames = 3

for _, record in ipairs(records) do
  maxPrefixLength = math.max(maxPrefixLength, #record.matchPrefix)
end

for _, record in ipairs(layoutRecords) do
  emu.addMemoryCallback(function(address, value)
    layoutSource = record
    layoutSourceExpires = frame + layoutSourceTtlFrames
  end, emu.callbackType.read, record.startAddress, record.endAddress,
    emu.cpuType.nes, emu.memType.nesMemory)
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

local function assignCell(address, tag)
  -- One logical source glyph has one current screen location. Moving it during
  -- a scroll must retire its previous location instead of duplicating it.
  for otherAddress, other in pairs(cells) do
    if otherAddress ~= address and other.recordId == tag.recordId
        and other.glyphIndex == tag.glyphIndex then
      cells[otherAddress] = nil
    end
  end
  cells[address] = tag
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
    assignCell(address, tag)
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
  if layoutSource and frame <= layoutSourceExpires then
    local physical = candidate.ppuAddress % 0x400
    local x = physical % 32
    local y = math.floor(physical / 32)
    local labelIndex = nil
    for _, label in ipairs(layoutSource.labels) do
      if x >= label.startX and x < label.endX
          and y >= label.startY and y < label.endY then
        labelIndex = label.index
        break
      end
    end
    layoutPending[candidate.ppuAddress % 0x400] = {
      recordId = layoutSource.id,
      labelIndex = labelIndex,
      value = value,
    }
  end
end

local function onNametableWrite(address, value)
  local oldLayout = layoutCells[address]
  local newLayout = layoutPending[address]
  if newLayout and newLayout.value == value then
    layoutCells[address] = newLayout
    layoutPending[address] = nil
    layoutDirty[newLayout.recordId] = true
    if oldLayout and oldLayout.recordId ~= newLayout.recordId then
      layoutDirty[oldLayout.recordId] = true
    end
  elseif oldLayout and oldLayout.value == value then
    -- A redraw of the same tile does not change what the Nametable cell means.
  elseif oldLayout then
    layoutCells[address] = nil
    layoutDirty[oldLayout.recordId] = true
  end
  layoutPending[address] = nil
  -- A later game write owns the cell. Only the exact queued destination/value
  -- inherits a tag; every unrelated write clears old provenance.
  untaggedWrites[address] = nil
  local pending = pendingUploads[address]
  if pending and pending.value == value then
    assignCell(address, pending)
    pendingUploads[address] = nil
    changed = true
  elseif cells[address] and cells[address].value == value then
    -- Preserve provenance when the game redraws an unchanged tile. Window
    -- refreshes frequently do this without reading the script byte again.
  elseif cells[address] then
    cells[address] = nil
    changed = true
    untaggedWrites[address] = value
  elseif address >= visibilityStart and address < visibilityEndExclusive then
    untaggedWrites[address] = value
  end
  pendingUploads[address] = nil
end

local function propagateCopiedCells()
  if next(untaggedWrites) == nil or next(previousCells) == nil then return end
  local votes = {}
  for destination, value in pairs(untaggedWrites) do
    for source, cell in pairs(previousCells) do
      local delta = destination - source
      if delta ~= 0 and delta % 32 == 0 and math.abs(delta) <= 128
          and cell.value == value then
        votes[delta] = (votes[delta] or 0) + 1
      end
    end
  end
  local bestDelta = nil
  local bestVotes = 0
  for delta, count in pairs(votes) do
    if count > bestVotes then
      bestDelta = delta
      bestVotes = count
    end
  end
  -- A repeated glyph can match by accident. Require a short sequence of
  -- agreeing cells before treating a write batch as a Nametable copy/scroll.
  if not bestDelta or bestVotes < 3 then return end
  local copied = 0
  for destination, value in pairs(untaggedWrites) do
    local source = destination - bestDelta
    local cell = previousCells[source]
    if cell and cell.value == value then
      assignCell(destination, cell)
      copied = copied + 1
      changed = true
    end
  end
  if copied > 0 then
    print(string.format(
      "DQGLYPH {\"type\":\"copy\",\"frame\":%d," ..
      "\"delta\":%d,\"cellCount\":%d}", frame, bestDelta, copied
    ))
  end
end

local function snapshotCells()
  previousCells = {}
  for address, cell in pairs(cells) do previousCells[address] = cell end
  untaggedWrites = {}
end

local function emitLayoutGroups()
  for recordId, _ in pairs(layoutDirty) do
    local count = 0
    local labelCounts = {}
    for _, owner in pairs(layoutCells) do
      if owner.recordId == recordId then
        count = count + 1
        if owner.labelIndex then
          labelCounts[owner.labelIndex] = (labelCounts[owner.labelIndex] or 0) + 1
        end
      end
    end
    local labels = {}
    for index, labelCount in pairs(labelCounts) do
      table.insert(labels, string.format(
        "{\"index\":%d,\"cellCount\":%d}", index, labelCount
      ))
    end
    print(string.format(
      "DQMENU {\"type\":\"group\",\"frame\":%d,\"recordId\":%s," ..
      "\"cellCount\":%d,\"labels\":[%s]}", frame, jsonString(recordId),
      count, table.concat(labels, ",")
    ))
  end
  layoutDirty = {}
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

local function emitSegmentCoverage()
  if not activeRecord then return end
  local parts = {}
  for _, segment in ipairs(activeRecord.segments) do
    local visible = 0
    for _, cell in pairs(cells) do
      if cell.recordId == activeRecord.id
          and cell.glyphIndex >= segment.sourceStart
          and cell.glyphIndex < segment.sourceEndExclusive then
        visible = visible + 1
      end
    end
    table.insert(parts, string.format(
      "{\"sourceStart\":%d,\"sourceEndExclusive\":%d," ..
      "\"visibleCount\":%d}",
      segment.sourceStart, segment.sourceEndExclusive, visible
    ))
  end
  print(string.format(
    "DQGLYPH {\"type\":\"coverage\",\"frame\":%d,\"recordId\":%s," ..
    "\"segments\":[%s]}", frame, jsonString(activeRecord.id),
    table.concat(parts, ",")
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
  propagateCopiedCells()
  emitLayoutGroups()
  if changed then
    emitVisibleRanges()
    emitSegmentCoverage()
    changed = false
  end

  local candidate = chooseSegment()
  if candidate then
    emptySinceFrame = nil
    if candidate ~= selectedSegment then
      selectedSegment = candidate
      print(string.format(
        "DQGLYPH {\"type\":\"segment\",\"frame\":%d," ..
        "\"recordId\":%s,\"sourceStart\":%d,\"sourceEndExclusive\":%d}",
        frame, jsonString(activeRecord.id), selectedSegment.sourceStart,
        selectedSegment.sourceEndExclusive
      ))
    end
  elseif activeRecord then
    if not emptySinceFrame then emptySinceFrame = frame end
    if frame - emptySinceFrame >= emptyGraceFrames then
      print(string.format(
        "DQGLYPH {\"type\":\"reset\",\"frame\":%d,\"recordId\":%s}",
        frame, jsonString(activeRecord.id)
      ))
      activeRecord = nil
      nextGlyph = 1
      selectedSegment = nil
      emptySinceFrame = nil
      stream = {}
      pendingBeforeMatch = {}
      pendingUploads = {}
      cells = {}
    end
  end
  drawSelectedSegment()
  snapshotCells()
  frame = frame + 1
  if layoutSource and frame > layoutSourceExpires then layoutSource = nil end
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
