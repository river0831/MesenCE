-- CHR-source-driven translated dialogue overlay. Record bytes and translated
-- presentation are generated from the local validated catalog and reviewable
-- translation spec. The ROM and emulated memory remain read-only.

-- __NES_TRANSLATION_DIALOGUE_CONFIG__

local foreground = 0xFFFFFF
local background = 0x000000
local frame = 0
local selector = nil
local expectingFirstByte = false
local stream = {}
local maxPrefixLength = 0
local activeRecord = nil
local activePage = 1
local visibleSinceFrame = -1
local activeIsVisible = false
local lastVisibilityWriteFrame = -1
local writesInVisibilityRegion = 0
local stableRegionFrames = 8

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

local function consumeSourceByte(value)
  table.insert(stream, value)
  if #stream > maxPrefixLength or activeRecord then return end
  for _, record in ipairs(records) do
    if prefixMatches(record.matchPrefix) then
      activeRecord = record
      activePage = 1
      visibleSinceFrame = frame
      activeIsVisible = false
      lastVisibilityWriteFrame = frame
      writesInVisibilityRegion = 0
      print(string.format(
        "DQDIALOGUE {\"type\":\"show\",\"frame\":%d,\"recordId\":%s}",
        frame, jsonString(record.id)
      ))
      return
    end
  end
end

local function onChrStreamSelector()
  selector = emu.read(0x3C, emu.memType.nesDebug) +
    emu.read(0x3D, emu.memType.nesDebug) * 256
  stream = {}
end

local function onChrWindowSetup()
  expectingFirstByte = true
end

local function onChrWindowWrite(address, value)
  if not expectingFirstByte or address ~= scratchFirstAddress then return end
  if cpuPc() ~= chrWindowWriterPc then return end
  expectingFirstByte = false
  consumeSourceByte(value)
end

local function onNametableWrite(address, value)
  if activeRecord
      and address >= visibilityStart
      and address < visibilityEndExclusive then
    writesInVisibilityRegion = writesInVisibilityRegion + 1
    lastVisibilityWriteFrame = frame
  end
end

local function drawDialogue()
  if not activeRecord or not activeIsVisible then return end
  emu.selectDrawSurface(emu.drawSurface.consoleScreen)
  emu.drawRectangle(
    activeRecord.x, activeRecord.y, activeRecord.width, activeRecord.height,
    background, true, 1
  )
  local page = activeRecord.pages[activePage]
  for index, line in ipairs(page) do
    emu.drawString(
      activeRecord.x + 4,
      activeRecord.y + 4 + (index - 1) * activeRecord.lineHeight,
      line, foreground, background, 0, 1
    )
  end
end

local function onEndFrame()
  if activeRecord
      and not activeIsVisible
      and frame - lastVisibilityWriteFrame >= stableRegionFrames then
    activeIsVisible = true
    visibleSinceFrame = frame
    print(string.format(
      "DQDIALOGUE {\"type\":\"visible\",\"frame\":%d,\"recordId\":%s}",
      frame, jsonString(activeRecord.id)
    ))
  elseif activeRecord
      and activeIsVisible
      and frame > visibleSinceFrame + hideGraceFrames
      and writesInVisibilityRegion >= clearWriteThreshold then
    if activePage < #activeRecord.pages then
      activePage = activePage + 1
      activeIsVisible = false
      lastVisibilityWriteFrame = frame
      print(string.format(
        "DQDIALOGUE {\"type\":\"page\",\"frame\":%d,\"recordId\":%s," ..
        "\"page\":%d}", frame, jsonString(activeRecord.id), activePage
      ))
    else
      print(string.format(
        "DQDIALOGUE {\"type\":\"hide\",\"frame\":%d,\"recordId\":%s," ..
        "\"regionWrites\":%d}",
        frame, jsonString(activeRecord.id), writesInVisibilityRegion
      ))
      activeRecord = nil
      activeIsVisible = false
    end
  end
  writesInVisibilityRegion = 0
  drawDialogue()
  frame = frame + 1
end

emu.addMemoryCallback(
  onChrStreamSelector, emu.callbackType.exec,
  chrStreamSelectorPc, chrStreamSelectorPc,
  emu.cpuType.nes, emu.memType.nesMemory
)
emu.addMemoryCallback(
  onChrWindowSetup, emu.callbackType.exec,
  chrWindowSetupPc, chrWindowSetupPc,
  emu.cpuType.nes, emu.memType.nesMemory
)
emu.addMemoryCallback(
  onChrWindowWrite, emu.callbackType.write,
  scratchFirstAddress, scratchFirstAddress,
  emu.cpuType.nes, emu.memType.nesMemory
)
emu.addMemoryCallback(
  onNametableWrite, emu.callbackType.write,
  0x0000, 0x07FF,
  emu.cpuType.nes, emu.memType.nesNametableRam
)
emu.addEventCallback(onEndFrame, emu.eventType.endFrame)

print(string.format(
  "DQDIALOGUE_READY records=%d maxPrefixLength=%d", #records, maxPrefixLength
))
