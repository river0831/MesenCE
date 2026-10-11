# Dragon Quest runtime findings

Confidence labels follow the project-wide scale documented in `database/schema.md`.

## Main command menu activation

- Record: `dq.menu.main`
- Physical PRG range: `$0459-$049A`
- Runtime CPU range: `$8459-$849A`
- Evidence: a visible main-menu open read the complete record at frame 15399
  in the original proof-of-concept run.
- Confidence: `runtime-confirmed`

## Main command menu deactivation

- Controller state is materialized in internal RAM `$0047`.
- The clean open/close capture read the main-menu record at frames 5633-5636.
- The visible cancel action produced input mask `$02` at frames 5992-6002.
- Menu drawing state bytes `$0096-$0098` cleared at frames 5997-5998, after
  which the visible menu was gone.
- Runtime rule: while `dq.menu.main` is active, the rising edge of input mask
  `$02` emits `text-hide`.
- Confidence: `runtime-confirmed` for this exact ROM and active record.

The input mask is stored on the database record rather than in the generic
resolver. It must not be assumed to mean “hide” for another record or game.

## Return to the main menu

- In the first lifecycle capture, the main-menu range was initially read at
  frames 5448-5451 and read again at frames 5644-5649 after returning from a
  child state.
- The existing ROM-read locator can therefore re-emit `text-show` after the
  child state has hidden or replaced the active translation.
- Confidence: `runtime-confirmed` for main-menu reactivation.

## Still unresolved

- The first child-menu run did not produce a distinct, reviewable text record
  inside the deliberately narrow candidate ROM window. Its labels may be
  generated from dynamic data or lie outside that window.
- No child-menu translation is in the database yet.
- Dialogue page boundaries and dialogue close behavior remain untested.
