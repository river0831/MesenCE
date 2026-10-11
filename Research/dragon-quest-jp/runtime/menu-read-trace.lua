-- Read-only Mesen debugger adapter for the Dragon Quest menu PoC.
-- The exact 32 KiB PRG is mapped at CPU $8000-$FFFF. The watched ranges are
-- database-backed records; the Python resolver decides which translation is
-- active and how it transitions.

local frame = 0
local previousInput = 0

emu.addEventCallback(function()
  frame = frame + 1
  local input = emu.read(0x47, emu.memType.nesDebug)
  if input ~= 0 and input ~= previousInput then
    print(string.format(
      "DQTRACE {\"type\":\"input\",\"frame\":%d,\"buttons\":%d}",
      frame, input
    ))
  end
  previousInput = input
end, emu.eventType.endFrame)

local function onRecordRead(address, value)
  local state = emu.getCpuState(emu.cpuType.nes)
  local pc = state.pc or state.PC or 0
  print(string.format(
    "DQTRACE {\"type\":\"rom-read\",\"frame\":%d,\"cpuAddress\":%d," ..
    "\"prgOffset\":%d,\"value\":%d,\"cpuPc\":%d}",
    frame, address, address - 0x8000, value, pc
  ))
end

-- dq.menu.strength: physical PRG $030F-$03F5
emu.addMemoryCallback(
  onRecordRead,
  emu.callbackType.read,
  0x830F,
  0x83F5,
  emu.cpuType.nes,
  emu.memType.nesMemory
)

-- dq.menu.main: physical PRG $0459-$049A
emu.addMemoryCallback(
  onRecordRead,
  emu.callbackType.read,
  0x8459,
  0x849A,
  emu.cpuType.nes,
  emu.memType.nesMemory
)

print("DQTRACE_READY records=dq.menu.main,dq.menu.strength")
