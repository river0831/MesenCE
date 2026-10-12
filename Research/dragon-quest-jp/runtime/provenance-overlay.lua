-- Database-driven overlay whose lifecycle comes from sourced Nametable cells.
-- It does not inspect controller input. Exact-ROM buffer layout and record
-- ranges are injected by Tools.NesTranslation.provenance.

-- __NES_TRANSLATION_PROVENANCE_CONFIG__

local foreground = 0xFFFFFF
local background = 0x000000
local stableFrames = 2
local restoreRatio = 0.80
local bulkClearThreshold = 8
local frame = 0
local activeSource = nil
local sourceExpiresAfterFrame = -1
local currentRecordId = nil
local bufferTags = {}
local pendingByValue = {}
local pendingClears = {}
local shadow = {}
local dirtyRecords = {}
local states = {}
local recordsById = {}

for _, record in ipairs(records) do
  recordsById[record.id] = record
  states[record.id] = {
    cellCount = 0,
    maxCellCount = 0,
    lastChangeFrame = -1,
    lastWriteFrame = -1,
  }
end

local function cpuPc()
  local state = emu.getCpuState(emu.cpuType.nes)
  return state.pc or state.PC or 0
end

local function jsonString(value) return string.format("%q", value) end
local function markDirty(recordId)
  if recordId then dirtyRecords[recordId] = true end
end

local function registerRecord(record)
  emu.addMemoryCallback(
    function(address, value)
      activeSource = {
        recordId = record.id,
        cpuAddress = address,
        readerPc = cpuPc(),
      }
      sourceExpiresAfterFrame = frame + sourceTtlFrames
      if currentRecordId ~= record.id then
        currentRecordId = record.id
        print(string.format(
          "DQPROVOVERLAY {\"type\":\"focus\",\"frame\":%d,\"recordId\":%s}",
          frame, jsonString(record.id)
        ))
      end
    end,
    emu.callbackType.read,
    record.startAddress,
    record.endAddress,
    emu.cpuType.nes,
    emu.memType.nesMemory
  )
end

for _, record in ipairs(records) do registerRecord(record) end

local function isBufferValueAddress(address)
  return ppuUpdateBuffer
      and address >= ppuUpdateBuffer.ramStart
      and address < ppuUpdateBuffer.ramEndExclusive
      and (address - ppuUpdateBuffer.ramStart) % ppuUpdateBuffer.entrySize
          == ppuUpdateBuffer.valueOffset
end

local function onBufferWrite(address, value)
  if not isBufferValueAddress(address) then return end
  if cpuPc() ~= ppuUpdateBuffer.writerPc then
    bufferTags[address] = nil
    return
  end
  if activeSource and frame <= sourceExpiresAfterFrame then
    bufferTags[address] = {
      recordId = activeSource.recordId,
      sourceCpuAddress = activeSource.cpuAddress,
      readerPc = activeSource.readerPc,
      value = value,
    }
  else
    bufferTags[address] = nil
  end
end

local function onBufferRead(address, value)
  local tag = bufferTags[address]
  if tag and tag.value == value then
    pendingByValue[value] = {
      recordId = tag.recordId,
      sourceCpuAddress = tag.sourceCpuAddress,
      readerPc = tag.readerPc,
      frame = frame,
    }
  end
end

if not ppuUpdateBuffer then
  error("provenance overlay requires runtime.ppuUpdateBuffer")
end

emu.addMemoryCallback(
  onBufferWrite,
  emu.callbackType.write,
  ppuUpdateBuffer.ramStart,
  ppuUpdateBuffer.ramEndExclusive - 1,
  emu.cpuType.nes,
  emu.memType.nesMemory
)
emu.addMemoryCallback(
  onBufferRead,
  emu.callbackType.read,
  ppuUpdateBuffer.ramStart,
  ppuUpdateBuffer.ramEndExclusive - 1,
  emu.cpuType.nes,
  emu.memType.nesMemory
)

local function tilePosition(address)
  local tableIndex = math.floor(address / 0x400)
  local tableOffset = address % 0x400
  if tableOffset >= 960 then return nil end
  return tableIndex, math.floor(tableOffset / 32), tableOffset % 32
end

local function onNametableWrite(address, value)
  local tableIndex, row, column = tilePosition(address)
  if not tableIndex then return end
  local old = shadow[address]
  local source = pendingByValue[value]
  if source and source.frame ~= frame then source = nil end
  if source then pendingByValue[value] = nil end
  if source then
    for _, clears in pairs(pendingClears) do clears[address] = nil end
    if old then markDirty(old.recordId) end
    markDirty(source.recordId)
    shadow[address] = {
      recordId = source.recordId,
      frame = frame,
      tableIndex = tableIndex,
      row = row,
      column = column,
    }
  elseif old and old.recordId then
    local clears = pendingClears[old.recordId]
    if not clears then
      clears = {}
      pendingClears[old.recordId] = clears
    end
    clears[address] = true
  else
    shadow[address] = {
      recordId = nil,
      frame = frame,
      tableIndex = tableIndex,
      row = row,
      column = column,
    }
  end
end

emu.addMemoryCallback(
  onNametableWrite,
  emu.callbackType.write,
  0x0000,
  0x07FF,
  emu.cpuType.nes,
  emu.memType.nesNametableRam
)

local function updateGroups()
  for recordId, _ in pairs(dirtyRecords) do
    local count, latestWriteFrame = 0, -1
    for _, cell in pairs(shadow) do
      if cell.recordId == recordId then
        count = count + 1
        latestWriteFrame = math.max(latestWriteFrame, cell.frame)
      end
    end
    local state = states[recordId]
    if state.cellCount ~= count then
      state.cellCount = count
      state.maxCellCount = math.max(state.maxCellCount, count)
      state.lastChangeFrame = frame
      state.lastWriteFrame = latestWriteFrame
      print(string.format(
        "DQPROVOVERLAY {\"type\":\"group\",\"frame\":%d," ..
        "\"recordId\":%s,\"cellCount\":%d,\"maxCellCount\":%d}",
        frame, jsonString(recordId), count, state.maxCellCount
      ))
    end
  end
  dirtyRecords = {}
end

local function applyBulkClears()
  for recordId, addresses in pairs(pendingClears) do
    local count = 0
    for _, _ in pairs(addresses) do count = count + 1 end
    if count >= bulkClearThreshold then
      for address, _ in pairs(addresses) do
        local cell = shadow[address]
        if cell and cell.recordId == recordId then
          cell.recordId = nil
          cell.frame = frame
        end
      end
      markDirty(recordId)
    end
  end
  pendingClears = {}
end

local function chooseRestoredRecord()
  local bestId, bestFrame = nil, -1
  for recordId, state in pairs(states) do
    if state.maxCellCount > 0
        and state.cellCount / state.maxCellCount >= restoreRatio
        and state.lastWriteFrame > bestFrame then
      bestId, bestFrame = recordId, state.lastWriteFrame
    end
  end
  return bestId
end

local function drawCurrentRecord()
  if not currentRecordId then return end
  local state = states[currentRecordId]
  if state.cellCount == 0 then
    if state.lastChangeFrame < 0 then return end
    local dismissed = currentRecordId
    currentRecordId = chooseRestoredRecord()
    print(string.format(
      "DQPROVOVERLAY {\"type\":\"hide\",\"frame\":%d," ..
      "\"recordId\":%s,\"restoredRecordId\":%s}",
      frame, jsonString(dismissed),
      currentRecordId and jsonString(currentRecordId) or "null"
    ))
    if not currentRecordId then return end
    state = states[currentRecordId]
  end
  if frame - state.lastChangeFrame < stableFrames then return end
  local record = recordsById[currentRecordId]
  emu.selectDrawSurface(emu.drawSurface.consoleScreen)
  for _, label in ipairs(record.labels) do
    emu.drawRectangle(
      label.clearX, label.clearY, label.clearWidth, label.clearHeight,
      background, true, 1
    )
    emu.drawString(label.x, label.y, label.text, foreground, background, 0, 1)
  end
end

local function onEndFrame()
  applyBulkClears()
  updateGroups()
  drawCurrentRecord()
  frame = frame + 1
  pendingByValue = {}
  if activeSource and frame > sourceExpiresAfterFrame then activeSource = nil end
end

emu.addEventCallback(onEndFrame, emu.eventType.endFrame)
print(string.format(
  "DQPROVOVERLAY_READY records=%d stableFrames=%d exactBuffer=true",
  #records, stableFrames
))
