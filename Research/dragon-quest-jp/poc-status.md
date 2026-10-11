# Translation PoC status

## Completed

- The database is bound to the exact Dragon Quest ROM SHA-256.
- The complete main menu is verified byte-for-byte at PRG `$0459-$049A`.
- Synthetic `rom-read` events resolve to one deduplicated translation command.
- Database validation, resolver lifecycle, renderer, replay, and Mesen trace-line
  parsing have automated tests.
- Mesen loads `runtime/menu-read-trace.lua` and emits `DQTRACE_READY` without
  using PPU monitoring or emulator-core changes.

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

Returning from a child state also re-read the verified main-menu range at
frames 5644-5649 in the first capture, so the existing ROM locator naturally
reactivates the main-menu translation. A translated child-menu record and
long-dialog handling remain the next milestones.
