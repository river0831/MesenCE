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

## Shared compressed-text dictionary

- Entering the empty item path caused a sequential read of physical PRG
  `$0858-$0A1E` at frame 5206, followed by a few reads near the selected entry.
- Code at CPU `$BE7A` checks whether a script byte is at least `$6D`, subtracts
  `$6D`, and uses the result as a dictionary index.
- It initializes the dictionary pointer to CPU `$8858` (physical PRG `$0858`)
  and advances through entries delimited by `$FA`.
- Therefore the large Japanese-looking region is a shared token dictionary,
  not one child-menu text record. Runtime identity must remain attached to the
  originating script record, not to the dictionary entry alone.
- Confidence: `code-confirmed` for the token threshold, dictionary base, and
  `$FA` entry delimiter; the semantic purpose of individual entries remains
  unconfirmed.

## Status summary and strength-detail windows

- In the attempted `つよさ` trace, the main-menu capture began at frame 54970
  and the next recorded input edge occurred at frame 55017.
- Physical PRG `$02D3-$030E` began being read at frame 55071 and continued to
  participate in drawing through frame 55863.
- The 60-byte region consists of window records terminated by `$FF`. Its five
  content rows contain fixed glyph bytes followed by dynamic-value operations
  (`$F0 $C5-$C7` and `$F1 $BA/$BC`). A later screenshot identifies this as
  the separate left-hand summary window: player name, レベル, HP, MP, G, and
  E. It is not the large `つよさ` detail window.
- A larger, adjacent group beginning at physical PRG `$030F` matches the
  right-hand detail window in the screenshot. Its rows are レベル, ちから,
  すばやさ, さいだいHP, さいだいMP, こうげき力, しゅび力, ぶき, よろい,
  and たて, each with a dynamic value or equipment-name field.
- No reads from `$030F` occurred in the first attempted trace, showing that the
  summary and detail windows must not be inferred from one another.
- In the corrected capture, input mask `$20` selected the second command at
  frame 1278 and confirmation mask `$01` occurred at frame 1318. The first
  `$030F` read occurred in that same frame. All 231 consecutive bytes through
  `$03F5` were read by frame 1331.
- Cancel mask `$02` occurred at frame 1610. Because the underlying main menu
  remained drawn and its ROM range was not read again, `dq.menu.strength`
  declares `returnToRecordId: dq.menu.main`; the generic resolver restores the
  parent translation without game-specific code.
- A subsequent production-adapter run (not the diagnostic replay) emitted the
  expected live sequence: `dq.menu.main` show at frame 1676,
  `dq.menu.strength` replace at frame 1740, and `dq.menu.main` replace at frame
  1968 after cancel.
- Confidence: `runtime-confirmed` for `$02D3-$030E` as the summary window and
  `$030F-$03F5` as the strength-detail record. Field meanings are
  `cross-validated` by byte decoding and the screenshot.

## Strength-detail visual overlay

- A read-only Lua overlay activates from the runtime-confirmed
  `dq.menu.strength` range and redraws only the ten static label areas.
- A visual check confirmed that the original Japanese labels are fully
  covered, the translated labels align with their rows, and the game's
  numeric and equipment values remain unobscured.
- The current prototype uses traditional/Japanese glyph variants available in
  Mesen's built-in debug font (`等級`, `攻撃力`, and `鎧甲`). Simplified Chinese
  requires a separate bitmap font and remains future display work.
- Multiple subsequent open/cancel cycles emitted stable `show` and `hide`
  events, and the translated labels disappeared with the strength window.
- Lifecycle confidence: `runtime-confirmed`. Layout confidence remains
  `visual-provisional` pending tests at additional window scales.
