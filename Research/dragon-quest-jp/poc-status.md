# Translation PoC status

## Strength menu path

- Database record `dq.menu.strength` covers physical PRG `$030F-$03F5`.
- A corrected runtime capture hit the record on the same frame as the confirm
  input and read the full range while the detail window was drawn.
- Replay of the real diagnostic trace produces main-menu show, strength-menu
  replace, then main-menu restore on cancel.
- Both activation and cancel-to-parent behavior are runtime-confirmed for the
  bound ROM.
- The production live adapter was then tested with the same visible flow. It
  emitted main-menu `show` at frame 1676, strength-menu `replace` at frame
  1740, and parent-menu `replace` at frame 1968 after cancel. The final event
  intentionally has no PRG offset because it is a database-declared parent
  restoration rather than a new ROM read.

## Completed

- The database is bound to the exact Dragon Quest ROM SHA-256.
- The complete main menu is verified byte-for-byte at PRG `$0459-$049A`.
- Synthetic `rom-read` events resolve to one deduplicated translation command.
- Database validation, resolver lifecycle, renderer, replay, and Mesen trace-line
  parsing have automated tests.
- Mesen loads `runtime/menu-read-trace.lua`, watches both confirmed database
  ranges, and emits `DQTRACE_READY` without using PPU monitoring or
  emulator-core changes.

## Live ground-truth result

At frame 15399, opening the visible main menu caused a physical PRG read at
`$0459`. The resolver produced exactly one display command for the matching
record, without PPU monitoring. The menu locator is therefore
`runtime-confirmed` for this exact ROM.

## Menu lifecycle result

Two bounded non-PPU captures established the first deactivation rule for this
exact ROM. The cancel button produces controller mask `$02`; in the clean
open/close run it first appeared at frame 5992, the menu drawing state cleared
at frames 5997-5998, and the visible menu disappeared. `dq.menu.main` therefore
uses a database-scoped, runtime-confirmed `dismissInputMask` of `$02`.

Returning from a child state may either re-read the verified main-menu range
or restore a database-declared parent record when the underlying menu remains
drawn. The strength-menu route implements the latter. Long-dialog handling
remains the next milestone.
