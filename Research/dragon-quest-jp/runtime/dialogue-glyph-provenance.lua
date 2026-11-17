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
local activeInstanceId = nil
local activeInstances = {}
local nextInstanceNumber = 1
local nextGlyph = 1
local pendingBeforeMatch = {}
local pendingUploads = {}
local cells = {}
local visibleCells = {}
local previousCells = {}
local untaggedWrites = {}
local changed = false
local selectedSegment = nil
local emptyGraceFrames = 20
local foreground = 0xFFFFFF
local background = 0x000000
-- Stable layout records and one-shot dictionary terms are separate provenance
-- lanes. Nested dictionary reads must not replace the parent menu/message
-- source that owns the surrounding write transaction.
local staticLayoutSource = nil
local staticLayoutSourceValue = nil
local staticLayoutSourceLabelIndex = nil
local layoutPending = {}
local layoutCells = {}
local layoutDirty = {}
local textRunWrites = {}
local textRunGlyphs = {}
local textCells = {}
local previousProjectedText = {}
local previousProjectedGlyphs = {}
local textCellsDirty = false
local previousProjectionKey = nil
local previousSourceProjectionKey = nil
local previousLayoutProjectionKey = nil
local discoveryNode = 1
local recordsByFirstByte = {}
local layoutRecordsById = {}
local readPpuState = emu.getState
local pendingModifiedCaptures = {}

for _, record in ipairs(records) do
  maxPrefixLength = math.max(maxPrefixLength, #record.matchPrefix)
  local first = record.matchPrefix[1]
  if first then
    recordsByFirstByte[first] = recordsByFirstByte[first] or {}
    table.insert(recordsByFirstByte[first], record)
  end
end

for _, record in ipairs(layoutRecords) do
  layoutRecordsById[record.id] = record
  emu.addMemoryCallback(function(address, value)
    if record.dynamic and address == record.startAddress then
      print(string.format(
        "DQTERM {\"type\":\"source-term\",\"frame\":%d,\"recordId\":%s}",
        frame, string.format("%q", record.id)
      ))
    end
    if not record.dynamic then
      staticLayoutSource = record
      staticLayoutSourceValue = value
      staticLayoutSourceLabelIndex = nil
      for _, label in ipairs(record.labels) do
        if label.sourceStartAddress and address >= label.sourceStartAddress
            and address <= label.sourceEndAddress then
          staticLayoutSourceLabelIndex = label.index
          break
        end
      end
    end
  end, emu.callbackType.read, record.startAddress, record.endAddress,
    emu.cpuType.nes, emu.memType.nesMemory)
end

local function cpuPc()
  local state = emu.getCpuState(emu.cpuType.nes)
  return state.pc or state.PC or 0
end

local function jsonString(value) return string.format("%q", value) end

local function tilePatternSignature(tileIndex, patternBase)
  local bytes = {}
  local address = patternBase + tileIndex * 16
  for offset = 0, 15 do
    table.insert(bytes, string.format("%02x",
      emu.read(address + offset, emu.memType.nesPpuMemory)))
  end
  return table.concat(bytes)
end

local function isKnownGlyphPattern(tileIndex, patternBase, cache)
  if cache[tileIndex] ~= nil then return cache[tileIndex] end
  local expected = glyphPatterns[tileIndex]
  local matches = expected ~= nil and
    expected[tilePatternSignature(tileIndex, patternBase)] == true
  cache[tileIndex] = matches
  return matches
end

local function prefixMatches(prefix)
  if #stream < #prefix then return false end
  for index = 1, #prefix do
    if stream[index] ~= prefix[index] then return false end
  end
  return true
end

local function observeCatalogByte(value)
  if discoveryNode == 0 then return end
  local node = discoveryNodes[discoveryNode]
  local nextNode = node and node.edges[value] or nil
  if not nextNode then
    discoveryNode = 0
    return
  end
  discoveryNode = nextNode
  for _, recordId in ipairs(discoveryNodes[discoveryNode].records) do
    print(string.format(
      "DQDISCOVERY {\"type\":\"catalog-record\",\"frame\":%d," ..
      "\"recordId\":%s}", frame, jsonString(recordId)
    ))
  end
end

local function assignCell(address, tag)
  -- One logical source glyph has one current screen location. Moving it during
  -- a scroll must retire its previous location instead of duplicating it.
  for otherAddress, other in pairs(cells) do
    if otherAddress ~= address and other.instanceId == tag.instanceId
        and other.glyphIndex == tag.glyphIndex then
      cells[otherAddress] = nil
    end
  end
  cells[address] = tag
  if tag.modifier then
    pendingModifiedCaptures[address] = tag
  end
end

local function emitModifiedCaptures()
  local state = readPpuState()
  local patternBase = state["ppu.control.backgroundPatternAddr"] or 0
  for address, tag in pairs(pendingModifiedCaptures) do
    local pageBase = math.floor(address / 0x400) * 0x400
    local within = address % 0x400
    local row = math.floor(within / 32)
    local column = within % 32
    local actualTile = emu.read(address, emu.memType.nesNametableRam)
    local parts = {}
    for dy = -1, 1 do
      for dx = -1, 1 do
        local targetRow = row + dy
        local targetColumn = column + dx
        if targetRow >= 0 and targetRow < 30 and targetColumn >= 0 and targetColumn < 32 then
          local target = pageBase + targetRow * 32 + targetColumn
          local tile = emu.read(target, emu.memType.nesNametableRam)
          parts[#parts + 1] = string.format(
            "{\"dx\":%d,\"dy\":%d,\"ciramAddress\":%d," ..
            "\"tileId\":%d,\"patternHex\":\"%s\"}",
            dx, dy, target, tile, tilePatternSignature(tile, patternBase))
        end
      end
    end
    print(string.format(
      "DQVOICE {\"frame\":%d,\"sourceBase\":%d,\"modifier\":%d," ..
      "\"ppuAddress\":%d,\"ciramAddress\":%d,\"tileId\":%d," ..
      "\"patternBase\":%d,\"patternHex\":\"%s\"," ..
      "\"basePatternHex\":\"%s\",\"neighborhood\":[%s]}",
      frame, tag.sourceValue, tag.modifier, 0x2000 + address, address,
      actualTile, patternBase, tilePatternSignature(actualTile, patternBase),
      tilePatternSignature(tag.sourceValue, patternBase), table.concat(parts, ",")))
  end
  pendingModifiedCaptures = {}
end

local function physicalNametableAddress(ppuAddress)
  -- Dragon Quest uses vertical mirroring, so CIRAM retains two distinct
  -- 0x400-byte Nametable pages.  Collapsing this to one page makes buffered
  -- writes for the second page impossible to pair with the subsequent
  -- nesNametableRam callback (whose address is in the 0x000-0x7FF domain).
  return ppuAddress % 0x800
end

local function alignCandidate(candidate, alreadyUploaded)
  if not activeRecord then return end
  local glyph = activeRecord.glyphs[nextGlyph]
  if not glyph or (not glyph.modifier and candidate.value ~= glyph.value) then return end
  local address = physicalNametableAddress(candidate.ppuAddress)
  if address % 0x400 >= 0x3C0 then return end
  local tag = {
    recordId = activeRecord.id,
    instanceId = activeInstanceId,
    characterId = activeInstanceId .. ":" .. tostring(glyph.index),
    glyphIndex = glyph.index,
    sourceOffset = glyph.sourceOffset,
    expandedIndex = glyph.expandedIndex,
    value = candidate.value,
    sourceValue = glyph.value,
    modifier = glyph.modifier,
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
  activeInstanceId = "msg-" .. tostring(nextInstanceNumber)
  nextInstanceNumber = nextInstanceNumber + 1
  nextGlyph = 1
  selectedSegment = nil
  activeInstances[activeInstanceId] = {
    record = record,
    emptySinceFrame = nil,
  }
  for _, candidate in ipairs(pendingBeforeMatch) do alignCandidate(candidate, true) end
  pendingBeforeMatch = {}
  print(string.format(
    "DQGLYPH {\"type\":\"record\",\"frame\":%d,\"recordId\":%s," ..
    "\"instanceId\":%s}",
    frame, jsonString(record.id), jsonString(activeInstanceId)
  ))
  print(string.format(
    "DQGLYPH {\"type\":\"instance-begin\",\"frame\":%d," ..
    "\"recordId\":%s,\"instanceId\":%s}",
    frame, jsonString(record.id), jsonString(activeInstanceId)
  ))
end

local function consumeSourceByte(value)
  observeCatalogByte(value)
  table.insert(stream, value)
  if #stream > maxPrefixLength then return end
  local candidates = recordsByFirstByte[stream[1]] or {}
  for _, record in ipairs(candidates) do
    if prefixMatches(record.matchPrefix) then activateRecord(record); return end
  end
end

local function onChrStreamSelector()
  -- A decoder invocation is a producer transaction, not the lifetime of the
  -- text it previously placed on screen. Start a fresh source match while
  -- retaining older instances until their own cells are no longer visible.
  activeRecord = nil
  activeInstanceId = nil
  nextGlyph = 1
  selectedSegment = nil
  stream = {}
  pendingBeforeMatch = {}
  discoveryNode = 1
end

local function onChrWindowSetup() expectingFirstByte = true end

local function onChrWindowWrite(address, value)
  if not expectingFirstByte or address ~= scratchFirstAddress then return end
  if cpuPc() ~= chrWindowWriterPc then return end
  expectingFirstByte = false
  consumeSourceByte(value)
end

local function currentProjection()
  local state = emu.getState()
  local temporary = state["ppu.tmpVideoRamAddr"] or 0
  local fineX = state["ppu.xScroll"] or 0
  local patternBase = state["ppu.control.backgroundPatternAddr"] or 0
  local scrollX = (temporary & 0x1F) * 8 + fineX
  if (temporary & 0x400) ~= 0 then scrollX = scrollX + 256 end
  local scrollY = ((temporary & 0x3E0) >> 2) +
    ((temporary & 0x7000) >> 12)
  if (temporary & 0x800) ~= 0 then scrollY = scrollY + 240 end
  return {
    scrollX = scrollX,
    scrollY = scrollY,
    patternBase = patternBase,
    key = tostring(scrollX) .. ":" .. tostring(scrollY) ..
      ":" .. tostring(patternBase),
  }
end

local function screenTilePixel(ppuAddress, projection)
  local offset = (ppuAddress - 0x2000) % 0x1000
  local within = offset % 0x400
  if within >= 0x3C0 then return nil, nil end
  local nameTable = math.floor(offset / 0x400)
  local worldX = (nameTable % 2) * 256 + (within % 32) * 8
  local worldY = math.floor(nameTable / 2) * 240 +
    math.floor(within / 32) * 8
  projection = projection or currentProjection()
  local screenX = (worldX - projection.scrollX) % 512
  local screenY = (worldY - projection.scrollY) % 480
  if screenX >= 256 or screenY >= 240 then return nil, nil end
  return screenX, screenY
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
  local layoutSource = staticLayoutSource
  local layoutSourceValue = staticLayoutSourceValue
  local layoutSourceLabelIndex = staticLayoutSourceLabelIndex
  local layoutMatches = layoutSource and
    (not layoutSourceLabelIndex or candidate.value == layoutSourceValue)
  if layoutMatches then
    local labelIndex = layoutSourceLabelIndex
    layoutPending[physicalNametableAddress(candidate.ppuAddress)] = {
      recordId = layoutSource.id,
      labelIndex = labelIndex,
      value = value,
    }
    -- A source read authorizes one producer-buffer write. Keeping this
    -- context latched would assign every later menu/map write to the last
    -- record read, even after that record's window has disappeared.
    staticLayoutSource = nil
    staticLayoutSourceValue = nil
    staticLayoutSourceLabelIndex = nil
  end
end

local function onNametableWrite(address, value)
  local within = address % 0x400
  if within < 0x3C0 then
    -- Keep the physical CIRAM contents even when this page is currently
    -- offscreen.  Visibility is projected from the live PPU scroll at the end
    -- of each frame instead of being frozen at write time.
    if textCells[address] ~= value then
      textCells[address] = value
      textCellsDirty = true
    end
  end
  local oldLayout = layoutCells[address]
  local newLayout = layoutPending[address]
  if newLayout and newLayout.value == value then
    layoutCells[address] = newLayout
    layoutPending[address] = nil
    layoutDirty[newLayout.recordId] = true
    if oldLayout and oldLayout.recordId ~= newLayout.recordId then
      layoutDirty[oldLayout.recordId] = true
    end
  elseif oldLayout then
    -- Tile values are not identities: a map/background redraw can write the
    -- same numeric tile that a former window used. Without a matching queued
    -- provenance owner, this later write ends the old cell's lifecycle.
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
  elseif within < 0x3C0 then
    untaggedWrites[address] = value
  end
  pendingUploads[address] = nil
end

local function sameCell(left, right)
  return left and right and left.instanceId == right.instanceId
    and left.glyphIndex == right.glyphIndex and left.value == right.value
end

local function projectVisibleCells(projection)
  if not changed and projection.key == previousSourceProjectionKey then
    return false
  end
  previousSourceProjectionKey = projection.key
  local projected = {}
  for address, cell in pairs(cells) do
    local physicalPage = math.floor(address / 0x400)
    local within = address % 0x400
    for verticalPage = 0, 1 do
      local logicalPage = physicalPage + verticalPage * 2
      local ppuAddress = 0x2000 + logicalPage * 0x400 + within
      local x, y = screenTilePixel(ppuAddress, projection)
      if x and y then
        local screenAddress = math.floor(y / 8) * 32 + math.floor(x / 8)
        if screenAddress >= visibilityStart
            and screenAddress < visibilityEndExclusive then
          projected[screenAddress] = cell
        end
      end
    end
  end
  local projectionChanged = false
  for address, cell in pairs(projected) do
    if not sameCell(cell, visibleCells[address]) then
      projectionChanged = true
      break
    end
  end
  if not projectionChanged then
    for address, _ in pairs(visibleCells) do
      if projected[address] == nil then
        projectionChanged = true
        break
      end
    end
  end
  visibleCells = projected
  return projectionChanged
end

local function projectVisibleText(projection)
  textCellsDirty = false
  previousProjectionKey = projection.key
  local projected = {}
  local projectedGlyphs = {}
  local patternBase = projection.patternBase or 0
  local glyphCache = {}
  for address, value in pairs(textCells) do
    local physicalPage = math.floor(address / 0x400)
    local within = address % 0x400
    -- Dragon Quest uses vertical mirroring: physical A is logical pages 0/2,
    -- and physical B is logical pages 1/3.  Try both aliases because either
    -- can be selected by the current vertical scroll position.
    for verticalPage = 0, 1 do
      local logicalPage = physicalPage + verticalPage * 2
      local ppuAddress = 0x2000 + logicalPage * 0x400 + within
      local x, y = screenTilePixel(ppuAddress, projection)
      if x and y then
        local screenAddress = math.floor(y / 8) * 32 + math.floor(x / 8)
        -- Content matching follows the whole visible PPU viewport.  The
        -- visibilityStart/End range belongs to the original dialogue-source
        -- tracer and deliberately covers only the lower dialogue window;
        -- applying it here silently drops menus and shop lists in the upper
        -- part of the screen.
        projected[screenAddress] = value
        projectedGlyphs[screenAddress] = isKnownGlyphPattern(
          value, patternBase, glyphCache)
      end
    end
  end
  textRunWrites = {}
  textRunGlyphs = {}
  local changedProjection = false
  for address, value in pairs(projected) do
    if previousProjectedText[address] ~= value
        or previousProjectedGlyphs[address] ~= projectedGlyphs[address] then
      textRunWrites[address] = value
      textRunGlyphs[address] = projectedGlyphs[address]
      changedProjection = true
    end
  end
  -- The incremental matcher retains its last screen grid. Explicitly blank
  -- cells that disappeared because the viewport moved to the other page.
  for address, _ in pairs(previousProjectedText) do
    if projected[address] == nil then
      textRunWrites[address] = 0x5F
      textRunGlyphs[address] = isKnownGlyphPattern(
        0x5F, patternBase, glyphCache)
      changedProjection = true
    end
  end
  previousProjectedText = projected
  previousProjectedGlyphs = projectedGlyphs
  return changedProjection
end

local function emitTextRuns()
  if next(textRunWrites) == nil then return end
  local addresses = {}
  for address, _ in pairs(textRunWrites) do table.insert(addresses, address) end
  table.sort(addresses)
  local runs = {}
  local current = nil
  for _, address in ipairs(addresses) do
    local row = math.floor(address / 32)
    local column = address % 32
    if not current or current.row ~= row
        or column ~= current.startColumn + #current.values then
      current = { row = row, startColumn = column, values = {}, glyphs = {} }
      table.insert(runs, current)
    end
    table.insert(current.values, textRunWrites[address])
    table.insert(current.glyphs, textRunGlyphs[address] == true)
  end
  local parts = {}
  for _, run in ipairs(runs) do
    local bytes = {}
    local glyphMask = {}
    for _, value in ipairs(run.values) do
      table.insert(bytes, string.format("%02x", value))
    end
    for _, isGlyph in ipairs(run.glyphs) do
      table.insert(glyphMask, isGlyph and "1" or "0")
    end
    table.insert(parts, string.format(
      "{\"row\":%d,\"startColumn\":%d,\"hex\":%s," ..
      "\"glyphMask\":%s}", run.row, run.startColumn,
      jsonString(table.concat(bytes)), jsonString(table.concat(glyphMask))
    ))
  end
  print(string.format(
    "DQRUN {\"type\":\"writes\",\"frame\":%d,\"runs\":[%s]}",
    frame, table.concat(parts, ",")
  ))
  textRunWrites = {}
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

local function projectedPhysicalCell(address, projection)
  local physicalPage = math.floor(address / 0x400)
  local within = address % 0x400
  for verticalPage = 0, 1 do
    local logicalPage = physicalPage + verticalPage * 2
    local ppuAddress = 0x2000 + logicalPage * 0x400 + within
    local x, y = screenTilePixel(ppuAddress, projection)
    if x and y then return x, y end
  end
  return nil, nil
end

local function emitLayoutGroups(projection)
  if projection.key ~= previousLayoutProjectionKey then
    previousLayoutProjectionKey = projection.key
    for _, owner in pairs(layoutCells) do
      layoutDirty[owner.recordId] = true
    end
  end
  for recordId, _ in pairs(layoutDirty) do
    local count = 0
    local labelCounts = {}
    local labelBounds = {}
    local labelCells = {}
    for address, owner in pairs(layoutCells) do
      if owner.recordId == recordId then
        count = count + 1
        -- A window is often assembled on the offscreen Nametable page and
        -- scrolled into view afterwards. Resolve rectangle-only labels from
        -- the retained physical cell after applying the current projection;
        -- classifying them when written would use the previously visible page.
        local x, y = projectedPhysicalCell(address, projection)
        local labelIndex = owner.labelIndex
        if not labelIndex and x and y then
          local record = layoutRecordsById[recordId]
          if record then
            for _, label in ipairs(record.labels) do
              if x < label.endX and x + 8 > label.startX
                  and y < label.endY and y + 8 > label.startY then
                labelIndex = label.index
                break
              end
            end
          end
        end
        if labelIndex then
          labelCounts[labelIndex] = (labelCounts[labelIndex] or 0) + 1
          if x and y then
            labelCells[labelIndex] = labelCells[labelIndex] or {}
            table.insert(labelCells[labelIndex],
              math.floor(y / 8) * 32 + math.floor(x / 8))
            local bounds = labelBounds[labelIndex]
            if not bounds then
              bounds = { minX = x, minY = y,
                maxX = x + 8, maxY = y + 8 }
              labelBounds[labelIndex] = bounds
            else
              bounds.minX = math.min(bounds.minX, x)
              bounds.minY = math.min(bounds.minY, y)
              bounds.maxX = math.max(bounds.maxX, x + 8)
              bounds.maxY = math.max(bounds.maxY, y + 8)
            end
          end
        end
      end
    end
    local labels = {}
    for index, labelCount in pairs(labelCounts) do
      local bounds = labelBounds[index]
      local cellsJson = {}
      table.sort(labelCells[index] or {})
      for _, address in ipairs(labelCells[index] or {}) do
        table.insert(cellsJson, tostring(address))
      end
      if bounds then
        table.insert(labels, string.format(
          "{\"index\":%d,\"cellCount\":%d,\"x\":%d,\"y\":%d," ..
          "\"width\":%d,\"height\":%d,\"cells\":[%s]}", index, labelCount,
          bounds.minX, bounds.minY, bounds.maxX - bounds.minX,
          bounds.maxY - bounds.minY, table.concat(cellsJson, ",")
        ))
      else
        table.insert(labels, string.format(
          "{\"index\":%d,\"cellCount\":%d}", index, labelCount
        ))
      end
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
  local instances = {}
  local glyphParts = {}
  for address, cell in pairs(visibleCells) do
    local row = math.floor(address / 32)
    local column = address % 32
    local key = cell.instanceId .. ":" .. tostring(row)
    local item = rows[key]
    if not item then
      item = { recordId = cell.recordId, instanceId = cell.instanceId,
        row = row, start = cell.glyphIndex,
        finish = cell.glyphIndex, count = 0 }
      rows[key] = item
    end
    item.start = math.min(item.start, cell.glyphIndex)
    item.finish = math.max(item.finish, cell.glyphIndex)
    item.count = item.count + 1
    local instance = instances[cell.instanceId]
    if not instance then
      instance = { recordId = cell.recordId, instanceId = cell.instanceId,
        minRow = row, maxRow = row, minColumn = column,
        maxColumn = column, count = 0, cells = {} }
      instances[cell.instanceId] = instance
    end
    instance.minRow = math.min(instance.minRow, row)
    instance.maxRow = math.max(instance.maxRow, row)
    instance.minColumn = math.min(instance.minColumn, column)
    instance.maxColumn = math.max(instance.maxColumn, column)
    instance.count = instance.count + 1
    table.insert(instance.cells, address)
    table.insert(glyphParts, string.format(
      "{\"recordId\":%s,\"instanceId\":%s,\"index\":%d,\"cell\":%d}",
      jsonString(cell.recordId), jsonString(cell.instanceId),
      cell.glyphIndex, address
    ))
  end
  local parts = {}
  local instanceParts = {}
  local screenCells = {}
  for address, _ in pairs(visibleCells) do table.insert(screenCells, address) end
  table.sort(screenCells)
  local cellParts = {}
  for _, address in ipairs(screenCells) do
    table.insert(cellParts, tostring(address))
  end
  for _, item in pairs(rows) do
    table.insert(parts, string.format(
      "{\"recordId\":%s,\"instanceId\":%s,\"row\":%d,\"start\":%d," ..
      "\"endExclusive\":%d,\"cellCount\":%d}",
      jsonString(item.recordId), jsonString(item.instanceId), item.row,
      item.start, item.finish + 1, item.count
    ))
  end
  for _, instance in pairs(instances) do
    table.sort(instance.cells)
    local addresses = {}
    for _, address in ipairs(instance.cells) do
      table.insert(addresses, tostring(address))
    end
    table.insert(instanceParts, string.format(
      "{\"recordId\":%s,\"instanceId\":%s,\"cellCount\":%d," ..
      "\"x\":%d,\"y\":%d,\"width\":%d,\"height\":%d," ..
      "\"cells\":[%s]}", jsonString(instance.recordId),
      jsonString(instance.instanceId), instance.count,
      instance.minColumn * 8, instance.minRow * 8,
      (instance.maxColumn - instance.minColumn + 1) * 8,
      (instance.maxRow - instance.minRow + 1) * 8,
      table.concat(addresses, ",")
    ))
  end
  print(string.format(
    "DQGLYPH {\"type\":\"visible-ranges\",\"frame\":%d," ..
    "\"cells\":[%s],\"glyphs\":[%s],\"rows\":[%s],\"instances\":[%s]}", frame,
    table.concat(cellParts, ","), table.concat(glyphParts, ","),
    table.concat(parts, ","),
    table.concat(instanceParts, ",")
  ))
end

local function emitSegmentCoverage(instanceId, instance)
  local record = instance.record
  local parts = {}
  for _, segment in ipairs(record.segments) do
    local visible = 0
    for _, cell in pairs(visibleCells) do
      if cell.instanceId == instanceId then
        for _, range in ipairs(segment.ranges) do
          if cell.glyphIndex >= range.start
              and cell.glyphIndex < range.endExclusive then
            visible = visible + 1
            break
          end
        end
      end
    end
    table.insert(parts, string.format(
      "{\"segmentId\":%s,\"visibleCount\":%d}",
      jsonString(segment.id), visible
    ))
  end
  print(string.format(
    "DQGLYPH {\"type\":\"coverage\",\"frame\":%d,\"recordId\":%s," ..
    "\"instanceId\":%s,\"segments\":[%s]}",
    frame, jsonString(record.id), jsonString(instanceId),
    table.concat(parts, ",")
  ))
end

local function chooseSegment()
  local newest = -1
  local record = nil
  for _, cell in pairs(visibleCells) do
    if activeRecord and cell.instanceId == activeInstanceId
        and cell.glyphIndex > newest then
      newest = cell.glyphIndex
      record = activeRecord
    end
  end
  if not record then return nil end
  for _, segment in ipairs(record.segments) do
    for _, range in ipairs(segment.ranges) do
      if newest >= range.start and newest < range.endExclusive then
        return segment
      end
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
  emitModifiedCaptures()
  local projection = currentProjection()
  local sourceProjectionChanged = projectVisibleCells(projection)
  local textProjectionChanged = projectVisibleText(projection)
  local frameHasSnapshotEvents = changed or next(layoutDirty) ~= nil
    or sourceProjectionChanged or textProjectionChanged
  emitLayoutGroups(projection)
  emitTextRuns()
  if changed or sourceProjectionChanged then
    emitVisibleRanges()
    for instanceId, instance in pairs(activeInstances) do
      emitSegmentCoverage(instanceId, instance)
    end
    changed = false
  end

  local candidate = chooseSegment()
  if candidate then
    if candidate ~= selectedSegment then
      frameHasSnapshotEvents = true
      selectedSegment = candidate
      print(string.format(
        "DQGLYPH {\"type\":\"segment\",\"frame\":%d," ..
        "\"recordId\":%s,\"instanceId\":%s,\"segmentId\":%s}",
        frame, jsonString(activeRecord.id), jsonString(activeInstanceId),
        jsonString(selectedSegment.id)
      ))
    end
  end

  -- Each decoded message owns an independent screen lifetime. A later
  -- decoder transaction may begin while cells from earlier messages are
  -- still visible (for example, consecutive shop prompts). Do not let the
  -- older instance block or terminate the newer one.
  local expiredInstances = {}
  for instanceId, instance in pairs(activeInstances) do
    local visible = false
    for _, cell in pairs(visibleCells) do
      if cell.instanceId == instanceId then
        visible = true
        break
      end
    end
    if visible then
      instance.emptySinceFrame = nil
    else
      if not instance.emptySinceFrame then instance.emptySinceFrame = frame end
      if frame - instance.emptySinceFrame >= emptyGraceFrames then
        table.insert(expiredInstances, instanceId)
      end
    end
  end
  for _, instanceId in ipairs(expiredInstances) do
      local instance = activeInstances[instanceId]
      local record = instance.record
      frameHasSnapshotEvents = true
      print(string.format(
        "DQGLYPH {\"type\":\"instance-end\",\"frame\":%d," ..
        "\"recordId\":%s,\"instanceId\":%s," ..
        "\"reason\":\"coverage-timeout\"}",
        frame, jsonString(record.id), jsonString(instanceId)
      ))
      print(string.format(
        "DQGLYPH {\"type\":\"reset\",\"frame\":%d,\"recordId\":%s," ..
        "\"instanceId\":%s," ..
        "\"reason\":\"coverage-timeout\"}",
        frame, jsonString(record.id), jsonString(instanceId)
      ))
      activeInstances[instanceId] = nil
      for address, cell in pairs(cells) do
        if cell.instanceId == instanceId then cells[address] = nil end
      end
      for address, cell in pairs(pendingUploads) do
        if cell.instanceId == instanceId then pendingUploads[address] = nil end
      end
      if activeInstanceId == instanceId then
        activeRecord = nil
        activeInstanceId = nil
        nextGlyph = 1
        selectedSegment = nil
      end
      changed = true
  end
  drawSelectedSegment()
  snapshotCells()
  if frameHasSnapshotEvents then
    print(string.format(
      "DQFRAME {\"type\":\"end\",\"frame\":%d}", frame
    ))
  end
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
