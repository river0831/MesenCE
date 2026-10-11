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
- Cancel mask `$02` occurred at frame 1610. An initial event-only
  interpretation treated the lack of a new main-menu read as a parent-menu
  restoration.
- A subsequent production-adapter run (not the diagnostic replay) emitted the
  expected live sequence: `dq.menu.main` show at frame 1676,
  `dq.menu.strength` replace at frame 1740, and `dq.menu.main` replace at frame
  1968 after cancel.
- A later visual overlay run disproved that interpretation: the same cancel
  closes both visible menus. Restoring `dq.menu.main` left an overlay over the
  game scene. The database relationship was removed, so strength-menu cancel
  now produces a complete hide. This visual result supersedes the earlier
  event-only conclusion.
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
- The original game-specific overlay was subsequently replaced by a generic
  template. Record ranges, deactivation relationships, display text, and
  native-screen layout now come from the validated game database.
- The database-driven main-menu overlay was visually calibrated so its clear
  rectangles preserve the game's full cursor tile and remove all Japanese
  glyphs in both columns. The final run confirmed cursor movement, main-to-
  strength replacement, strength cancel-to-hide, and direct main-menu hide.
- Main-menu layout confidence: `visual-provisional`; both overlay lifecycles
  are `runtime-confirmed` for the bound ROM.

## Lightweight Nametable provenance

- A read-only prototype now attaches the active database record ID to a shadow
  copy of physical Nametable RAM. It uses Mesen's `nesNametableRam` write
  callback, so cartridge mirroring is already resolved to the 2 KiB CIRAM
  address written by the game.
- In the validation run, `dq.menu.main` was first read at frame 2970. Tagged
  writes grew over frames 2971-2974 into 113 cells with bounds table 0,
  rows 3-11, columns 14-27. This is a 14-by-9 rectangular window region,
  including its background/border writes rather than glyph cells alone.
- `dq.menu.strength` was first read at frame 3069. Its tagged writes grew over
  frames 3070-3083 into 308 cells with bounds table 0, rows 6-27,
  columns 12-25: a 14-by-22 rectangle.
- As the strength window was drawn, the main-menu tagged cell count fell from
  111 to 88, 64, and then 40. This directly observes higher-layer Nametable
  writes replacing the overlapping lower-layer provenance.
- On cancel, the strength group shrank by 28 cells per frame from frame 3385
  until it reached zero at frame 3395. The remaining main-menu group then
  shrank to zero by frame 3401. This independently confirms that this action
  closes both windows; the lower menu was not restored in this scenario.
- The three-frame context remained active because continuing source reads
  refreshed it while the window was rendered over multiple frames. The result
  validates lightweight temporal source propagation for these two records,
  but does not prove it will separate unrelated writes in other games.
- Confidence: `runtime-confirmed` for the observed Nametable bounds,
  overwrite sequence, and close-to-zero lifecycle in this exact ROM;
  `semantic-probable` for treating the temporal tag as true byte-level source
  provenance until the intermediate RAM PPU-update buffer is traced.

## PPU update buffer provenance

- A second diagnostic propagated the temporary record tag into CPU RAM and
  correlated tagged RAM reads with same-value physical Nametable writes.
- All successful correlations used RAM `$0302-$036E`. Addresses advance by
  three bytes, identifying the third byte of repeated buffer entries.
- The producer routine at CPU `$ABA4-$ABBA` stores three bytes per entry at
  `$0300,X`: high PPU address, low PPU address, then tile value. The tile-value
  store is at `$ABB8`; zero-page `$04` is the buffer cursor and `$C0` is the
  checked capacity.
- The NMI uploader loop at `$AB30-$AB4D` reads the high address at `$AB36` and
  writes it to `$2006` at `$AB39`; it reads/writes the low address at
  `$AB3D/$AB40`, then reads the tile value at `$AB44` and writes it to `$2007`
  at `$AB47`.
- Mesen callbacks reported producer PC `$ABBB`, consumer PC `$AB47`, and PPU
  writer PC `$AB4B`. Callback PC values point just after or within the observed
  instruction, consistent with the decoded loop above.
- Every successful RAM-read-to-Nametable-write correlation had the same clock
  delta of 5. The main menu produced four uploads per detected data slot;
  the strength window produced eleven, matching their multi-frame drawing
  sequences.
- This establishes a concrete path for this ROM:
  known text record -> `$0300` triple buffer -> NMI upload loop -> Nametable.
- Confidence: `code-confirmed` for the buffer format, producer, and uploader;
  `runtime-confirmed` for record-tagged data slots `$0302-$036E` in this run.

## Exact buffer-to-Nametable propagation

- The confirmed buffer description is now database data rather than Lua code:
  RAM `$0300-$03BF`, three-byte entries, with PPU high address at offset 0,
  low address at offset 1, and tile value at offset 2.
- The shadow Nametable adapter tags only value slots `$0302 + 3n`. A tagged
  slot must subsequently be read by the uploader before the matching
  Nametable write inherits its record ID. Other Nametable writes clear prior
  source metadata normally.
- A validation run using this exact path reproduced the earlier results:
  `dq.menu.main` reached 113 cells at rows 3-11, columns 14-27;
  `dq.menu.strength` reached 308 cells at rows 6-27, columns 12-25.
- Strength drawing again reduced the main group from 111 to 88, 64, and 40
  cells. Cancel reduced strength to zero and then main to zero. The exact
  buffer path therefore preserves show, overwrite, and clear lifecycle events
  without assigning source from a broad Nametable-write time window.
- A short TTL is still used between a known ROM record read and production of
  its buffer entry. Replacing that remaining correlation would require tracing
  the text decoder's register/table transformations or instrumenting the
  confirmed producer routine with an explicit render context.
- Confidence: `runtime-confirmed` for exact buffer-to-Nametable propagation;
  `semantic-probable` for the remaining ROM-read-to-buffer association.

## Provenance-driven overlay lifecycle

- A visual adapter now selects the newest sourced Nametable group, waits for
  two stable frames, and draws its database labels without reading controller
  input or using `deactivation.dismissInputMask`.
- The first visual run exposed that cursor movement replaces one background
  cell at a time without a text source tag. Treating every such write as group
  invalidation caused a two-frame translation flicker and gradually reduced
  the main group from 113 to 105 cells.
- The adapter now batches untagged overwrites per frame. Fewer than eight are
  treated as cursor/dynamic-field changes and preserve the region identity;
  eight or more are a bulk clear. Actual window open/close operations update
  roughly 28 cells per frame, so they remain unambiguously detected.
- A repeat visual run confirmed that repeated cursor movement no longer
  flickers. Opening strength suppresses the lower menu immediately, its group
  grows to 308 cells, and cancel drives it to zero and hides the overlay.
- The strength window's three equipment-label clear rectangles were reduced
  from 78 to 58 pixels and shifted right. Visual review confirmed that 武器,
  鎧甲, and 盾牌 no longer cover their dynamic right-hand equipment values.
- Confidence: `runtime-confirmed` for cursor-stable display, main-to-strength
  focus replacement, and strength hide in the tested flow. The threshold is a
  generic adapter policy but still needs validation on dialogue animation and
  other games before it can be considered a universal default.
