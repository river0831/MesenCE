-- Lightweight, read-only Nametable provenance prototype.
-- Known text reads open a short source context. Nametable writes inherit the
-- record ID in a shadow table; later untagged writes replace that metadata.

-- __NES_TRANSLATION_PROVENANCE_CONFIG__

local frame = 0
local activeSource = nil
local sourceExpiresAfterFrame = -1
local shadow = {}
local dirtyRecords = {}

local function cpuPc()
  local state = emu.getCpuState(emu.cpuType.nes)
  return state.pc or state.PC or 0
end

local function jsonString(value) return string.format("%q", value) end
local function markDirty(recordId)
  if recordId then dirtyRecords[recordId] = true end
end

local function setSource(record, address, value)
  activeSource = {
    recordId = record.id,
    cpuAddress = address,
    value = value,
    readerPc = cpuPc(),
  }
  sourceExpiresAfterFrame = frame + sourceTtlFrames
end

local function registerRecord(record)
  emu.addMemoryCallback(
    function(address, value)
      local changed = not activeSource or activeSource.recordId ~= record.id
      setSource(record, address, value)
      if changed then
        print(string.format(
          "DQPROV {\"type\":\"source\",\"frame\":%d," ..
          "\"recordId\":%s,\"cpuAddress\":%d,\"readerPc\":%d}",
          frame, jsonString(record.id), address, activeSource.readerPc
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
  local source = nil
  if activeSource and frame <= sourceExpiresAfterFrame then source = activeSource end
  if old then markDirty(old.recordId) end
  if source then markDirty(source.recordId) end

  shadow[address] = {
    tileId = value,
    recordId = source and source.recordId or nil,
    sourceCpuAddress = source and source.cpuAddress or nil,
    readerPc = source and source.readerPc or nil,
    writerPc = cpuPc(),
    frame = frame,
    tableIndex = tableIndex,
    row = row,
    column = column,
  }
end

-- Absolute callbacks use physical 2 KiB CIRAM addresses after mirroring.
emu.addMemoryCallback(
  onNametableWrite,
  emu.callbackType.write,
  0x0000,
  0x07FF,
  emu.cpuType.nes,
  emu.memType.nesNametableRam
)

local function emitGroups()
  for recordId, _ in pairs(dirtyRecords) do
    local count, minTable, maxTable = 0, 99, -1
    local minRow, maxRow, minColumn, maxColumn = 99, -1, 99, -1
    local latestFrame = -1
    for _, cell in pairs(shadow) do
      if cell.recordId == recordId then
        count = count + 1
        minTable, maxTable = math.min(minTable, cell.tableIndex), math.max(maxTable, cell.tableIndex)
        minRow, maxRow = math.min(minRow, cell.row), math.max(maxRow, cell.row)
        minColumn, maxColumn = math.min(minColumn, cell.column), math.max(maxColumn, cell.column)
        latestFrame = math.max(latestFrame, cell.frame)
      end
    end
    print(string.format(
      "DQPROV {\"type\":\"group\",\"frame\":%d,\"recordId\":%s," ..
      "\"cellCount\":%d,\"tableMin\":%d,\"tableMax\":%d," ..
      "\"rowMin\":%d,\"rowMax\":%d,\"columnMin\":%d," ..
      "\"columnMax\":%d,\"latestWriteFrame\":%d}",
      frame, jsonString(recordId), count,
      count > 0 and minTable or -1, count > 0 and maxTable or -1,
      count > 0 and minRow or -1, count > 0 and maxRow or -1,
      count > 0 and minColumn or -1, count > 0 and maxColumn or -1,
      latestFrame
    ))
  end
  dirtyRecords = {}
end

local function onEndFrame()
  emitGroups()
  frame = frame + 1
  if activeSource and frame > sourceExpiresAfterFrame then activeSource = nil end
end

emu.addEventCallback(onEndFrame, emu.eventType.endFrame)
print(string.format("DQPROV_READY records=%d sourceTtlFrames=%d", #records, sourceTtlFrames))
