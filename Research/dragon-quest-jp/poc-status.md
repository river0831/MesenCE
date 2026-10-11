# Translation PoC status

## Strength menu path

- Database record `dq.menu.strength` covers physical PRG `$030F-$03F5`.
- A corrected runtime capture hit the record on the same frame as the confirm
  input and read the full range while the detail window was drawn.
- Replay of the real diagnostic trace originally modeled a main-menu restore
  after strength-menu cancel. A later visual overlay run showed that the game
  actually closes both menus on that input, so the database now hides the
  complete menu overlay instead.
- Both strength activation and cancel-to-hide behavior are runtime-confirmed
  for the bound ROM.
- The production live adapter was then tested with the same visible flow. It
  emitted main-menu `show` at frame 1676, strength-menu `replace` at frame
  1740. Its earlier parent-menu `replace` at frame 1968 reflected the now
  superseded database relationship, not the visible game lifecycle.
- The first console-screen overlay now replaces all ten static Japanese labels
  while preserving the original dynamic numbers and equipment values. Its
  native-coordinate layout has passed one visual check.
- Repeated open/cancel cycles confirmed that the overlay activates again on
  each strength-record read and disappears on the verified cancel input.
- Presentation text, clear rectangles, and coordinates for both the main menu
  and strength menu now live in the game database. A generic launcher injects
  them into a game-agnostic Lua template after ROM validation.
- Final visual calibration preserves the complete moving cursor and removes
  all original labels in both menu columns. Runtime logs confirmed main-menu
  show, strength replacement, strength cancel-to-hide, and direct main-menu
  hide in the database-driven adapter.

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

Returning from a child state may re-read the verified main-menu range, restore
a database-declared parent record, or close the complete menu stack. Visual
validation established that the strength-menu route uses the last behavior.
Long-dialog handling remains the next milestone.
