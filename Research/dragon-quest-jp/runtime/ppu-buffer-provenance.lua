-- Diagnostic bridge from known ROM text reads through CPU RAM to Nametable.
--
-- This is lightweight provenance rather than full CPU taint tracking:
--   1. a known text read opens a bounded source context;
--   2. CPU RAM writes during that context inherit the record ID;
--   3. a tagged RAM read becomes a short-lived upload candidate;
--   4. a same-value Nametable write links the RAM cell to the PPU destination.

-- __NES_TRANSLATION_PROVENANCE_CONFIG__

local frame = 0
local activeSource = nil
local sourceExpiresAfterFrame = -1
local ramTags = {}
local recentReadsByValue = {}
local hits = {}
local maxClockDelta = 512

local function cpuPc()
  local state = emu.getCpuState(emu.cpuType.nes)
  return state.pc or state.PC or 0
end

local function masterClock()
  return emu.getMasterClock()
end

local function jsonString(value) return string.format("%q", value) end

local function registerRecord(record)
  emu.addMemoryCallback(
    function(address, value)
      activeSource = {
        recordId = record.id,
        sourceCpuAddress = address,
        readerPc = cpuPc(),
      }
      sourceExpiresAfterFrame = frame + sourceTtlFrames
    end,
    emu.callbackType.read,
    record.startAddress,
    record.endAddress,
    emu.cpuType.nes,
    emu.memType.nesMemory
  )
end

for _, record in ipairs(records) do registerRecord(record) end

local function onRamWrite(address, value)
  if activeSource and frame <= sourceExpiresAfterFrame then
    ramTags[address] = {
      recordId = activeSource.recordId,
      sourceCpuAddress = activeSource.sourceCpuAddress,
      readerPc = activeSource.readerPc,
      value = value,
      taggedFrame = frame,
      producerPc = cpuPc(),
    }
  else
    ramTags[address] = nil
  end
end

local function onRamRead(address, value)
  local tag = ramTags[address]
  if tag and tag.value == value then
    recentReadsByValue[value] = {
      recordId = tag.recordId,
      sourceCpuAddress = tag.sourceCpuAddress,
      readerPc = tag.readerPc,
      ramAddress = address,
      producerPc = tag.producerPc,
      consumerPc = cpuPc(),
      clock = masterClock(),
      frame = frame,
    }
  end
end

emu.addMemoryCallback(
  onRamWrite,
  emu.callbackType.write,
  0x0000,
  0x07FF,
  emu.cpuType.nes,
  emu.memType.nesMemory
)

emu.addMemoryCallback(
  onRamRead,
  emu.callbackType.read,
  0x0000,
  0x07FF,
  emu.cpuType.nes,
  emu.memType.nesMemory
)

local function onNametableWrite(address, value)
  local candidate = recentReadsByValue[value]
  if not candidate or candidate.frame ~= frame then return end

  local delta = masterClock() - candidate.clock
  if delta < 0 or delta > maxClockDelta then return end

  local key = candidate.recordId .. ":" .. tostring(candidate.ramAddress)
  local hit = hits[key]
  if not hit then
    hit = {
      recordId = candidate.recordId,
      ramAddress = candidate.ramAddress,
      producerPc = candidate.producerPc,
      consumerPc = candidate.consumerPc,
      ppuWriterPc = cpuPc(),
      count = 0,
      minClockDelta = delta,
      maxClockDelta = delta,
      firstFrame = frame,
      lastFrame = frame,
      ppuMin = address,
      ppuMax = address,
    }
    hits[key] = hit
  end
  hit.count = hit.count + 1
  hit.minClockDelta = math.min(hit.minClockDelta, delta)
  hit.maxClockDelta = math.max(hit.maxClockDelta, delta)
  hit.lastFrame = frame
  hit.ppuMin = math.min(hit.ppuMin, address)
  hit.ppuMax = math.max(hit.ppuMax, address)
end

emu.addMemoryCallback(
  onNametableWrite,
  emu.callbackType.write,
  0x0000,
  0x07FF,
  emu.cpuType.nes,
  emu.memType.nesNametableRam
)

local function emitHits()
  local summaries = {}
  for _, hit in pairs(hits) do
    local summary = summaries[hit.recordId]
    if not summary then
      summary = {
        recordId = hit.recordId,
        ramMin = hit.ramAddress,
        ramMax = hit.ramAddress,
        candidateCount = 0,
        hitCount = 0,
        producerPc = hit.producerPc,
        consumerPc = hit.consumerPc,
        ppuWriterPc = hit.ppuWriterPc,
        minClockDelta = hit.minClockDelta,
        maxClockDelta = hit.maxClockDelta,
      }
      summaries[hit.recordId] = summary
    end
    summary.ramMin = math.min(summary.ramMin, hit.ramAddress)
    summary.ramMax = math.max(summary.ramMax, hit.ramAddress)
    summary.candidateCount = summary.candidateCount + 1
    summary.hitCount = summary.hitCount + hit.count
    summary.minClockDelta = math.min(summary.minClockDelta, hit.minClockDelta)
    summary.maxClockDelta = math.max(summary.maxClockDelta, hit.maxClockDelta)
  end
  for _, summary in pairs(summaries) do
    print(string.format(
      "DQBUFFER {\"type\":\"buffer-summary\",\"recordId\":%s," ..
      "\"ramMin\":%d,\"ramMax\":%d,\"candidateCount\":%d," ..
      "\"hitCount\":%d,\"producerPc\":%d,\"consumerPc\":%d," ..
      "\"ppuWriterPc\":%d," ..
      "\"minClockDelta\":%d,\"maxClockDelta\":%d}",
      jsonString(summary.recordId), summary.ramMin, summary.ramMax,
      summary.candidateCount, summary.hitCount, summary.producerPc,
      summary.consumerPc, summary.ppuWriterPc,
      summary.minClockDelta, summary.maxClockDelta
    ))
  end
end

local function onEndFrame()
  frame = frame + 1
  recentReadsByValue = {}
  if activeSource and frame > sourceExpiresAfterFrame then activeSource = nil end
end

emu.addEventCallback(onEndFrame, emu.eventType.endFrame)
emu.addEventCallback(emitHits, emu.eventType.scriptEnded)
print(string.format(
  "DQBUFFER_READY records=%d sourceTtlFrames=%d maxClockDelta=%d",
  #records, sourceTtlFrames, maxClockDelta
))
