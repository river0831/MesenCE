-- Generic database-driven label overlay template.
-- The launcher replaces the marker below with validated record configuration.

-- __NES_TRANSLATION_CONFIG__

local foreground = 0xFFFFFF
-- Mesen uses 0x00 as opaque and 0xFF as transparent for drawing commands.
local background = 0x000000
local activeRecord = nil
local previousInput = 0
local recordById = {}

for _, record in ipairs(records) do
  recordById[record.id] = record
end

local function setActiveRecord(record, reason, address)
  if activeRecord == record then
    return
  end
  activeRecord = record
  print(string.format(
    "NESOVERLAY {\"type\":\"%s\",\"recordId\":\"%s\",\"cpuAddress\":%s}",
    reason, record.id, address and tostring(address) or "null"
  ))
end

local function registerRecord(record)
  emu.addMemoryCallback(
    function(address, value)
      setActiveRecord(record, activeRecord and "replace" or "show", address)
    end,
    emu.callbackType.read,
    record.startAddress,
    record.endAddress,
    emu.cpuType.nes,
    emu.memType.nesMemory
  )
end

for _, record in ipairs(records) do
  registerRecord(record)
end

local function drawActiveRecord()
  if not activeRecord then
    return
  end
  emu.selectDrawSurface(emu.drawSurface.consoleScreen)
  for _, label in ipairs(activeRecord.labels) do
    emu.drawRectangle(
      label.clearX,
      label.clearY,
      label.clearWidth,
      label.clearHeight,
      background,
      true,
      1
    )
    emu.drawString(label.x, label.y, label.text, foreground, background, 0, 1)
  end
end

local function onEndFrame()
  local input = emu.read(inputAddress, emu.memType.nesDebug)
  if activeRecord
      and activeRecord.dismissInputMask
      and input ~= previousInput
      and input & activeRecord.dismissInputMask ~= 0 then
    local dismissed = activeRecord
    if dismissed.returnToRecordId then
      setActiveRecord(recordById[dismissed.returnToRecordId], "replace", nil)
    else
      activeRecord = nil
      print(string.format(
        "NESOVERLAY {\"type\":\"hide\",\"recordId\":\"%s\"}",
        dismissed.id
      ))
    end
  end
  previousInput = input
  drawActiveRecord()
end

emu.addEventCallback(onEndFrame, emu.eventType.endFrame)
print(string.format("NESOVERLAY_READY records=%d", #records))
