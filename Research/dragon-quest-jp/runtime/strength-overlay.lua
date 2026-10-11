-- Visual proof of concept for the runtime-confirmed Dragon Quest strength menu.
--
-- This script does not modify emulated memory or the ROM. It covers only the
-- static Japanese labels; the game's original numeric and equipment values
-- remain visible. Mesen's built-in debug font contains the traditional/Japanese
-- glyph forms used below, which keeps this prototype outside the emulator core.

local strengthStart = 0x830F
local strengthEnd = 0x83F5
local dismissInputMask = 0x02
local overlayActive = false
local previousInput = 0

local clearX = 100
local clearWidth = 78
local firstLabelY = 66
local rowHeight = 16
local foreground = 0xFFFFFF
-- Mesen's Lua drawing API uses 0x00 as opaque and 0xFF as transparent.
local background = 0x000000

local labels = {
  { x = 132, text = "等級:" },
  { x = 132, text = "力量:" },
  { x = 132, text = "敏捷:" },
  { x = 123, text = "最大HP:" },
  { x = 123, text = "最大MP:" },
  { x = 126, text = "攻撃力:" },
  { x = 126, text = "防御力:" },
  { x = 132, text = "武器:" },
  { x = 132, text = "鎧甲:" },
  { x = 132, text = "盾牌:" },
}

local function drawOverlay()
  emu.selectDrawSurface(emu.drawSurface.consoleScreen)
  for index, label in ipairs(labels) do
    local y = firstLabelY + (index - 1) * rowHeight
    emu.drawRectangle(clearX, y - 2, clearWidth, 12, background, true, 1)
    emu.drawString(label.x, y, label.text, foreground, background, 0, 1)
  end
end

local function onStrengthRead(address, value)
  if not overlayActive then
    overlayActive = true
    print(string.format(
      "DQOVERLAY {\"type\":\"show\",\"recordId\":\"dq.menu.strength\"," ..
      "\"cpuAddress\":%d}", address
    ))
  end
end

local function onEndFrame()
  local input = emu.read(0x47, emu.memType.nesDebug)
  if overlayActive and input ~= previousInput and input & dismissInputMask ~= 0 then
    overlayActive = false
    print("DQOVERLAY {\"type\":\"hide\",\"recordId\":\"dq.menu.strength\"}")
  end
  previousInput = input

  if overlayActive then
    drawOverlay()
  end
end

emu.addMemoryCallback(
  onStrengthRead,
  emu.callbackType.read,
  strengthStart,
  strengthEnd,
  emu.cpuType.nes,
  emu.memType.nesMemory
)
emu.addEventCallback(onEndFrame, emu.eventType.endFrame)

print("DQOVERLAY_READY record=dq.menu.strength mode=static-labels")
