-- Read-only Mesen debugger adapter for the Dragon Quest menu PoC.
-- The exact 32 KiB PRG is mapped at CPU $8000-$FFFF, so CPU $8459-$849A
-- corresponds to physical PRG $0459-$049A (the complete eight-entry menu).

local frame = 0

emu.addEventCallback(function()
  frame = frame + 1
end, emu.eventType.endFrame)

emu.addMemoryCallback(function(address, value)
  local state = emu.getCpuState(emu.cpuType.nes)
  local pc = state.pc or state.PC or 0
  print(string.format(
    "DQTRACE {\"type\":\"rom-read\",\"frame\":%d,\"cpuAddress\":%d," ..
    "\"prgOffset\":%d,\"value\":%d,\"cpuPc\":%d}",
    frame, address, address - 0x8000, value, pc
  ))
end, emu.callbackType.read, 0x8459, 0x849A, emu.cpuType.nes, emu.memType.nesMemory)

print("DQTRACE_READY menu=dq.menu.main cpuStart=33881 cpuEnd=33946")
