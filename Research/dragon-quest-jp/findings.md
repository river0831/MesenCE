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

## First NPC-dialogue capture

- A bounded run captured the main menu at frame 10467, the `はなす` selection
  beginning at frame 10489, and subsequent advance inputs at frames 10516,
  10649, and 10668.
- One renderer fetches record data with `LDA ($99),Y` at CPU `$BD30`; a Mesen
  read callback observes `$BD32` after the effective read. The same indirect
  instruction also performs bus reads of zero-page `$99/$9A`, so those pointer
  bytes must be filtered rather than reported as text.
- The second capture confirmed that the effective reads at this site came from
  PRG. The earlier apparent absence of a PRG source was an instrumentation
  error, not evidence for a RAM-backed dialogue stream.
- CPU `$BE6A` is the stronger identity hook: the accumulator holds the decoded
  source token immediately before comparison with `$6D`, while `$99/$9A`
  identify its current source. Capturing this execution point distinguishes an
  originating token from later reads used to search or expand the dictionary.
- Dictionary output was observed at frames 10529-10613. Reads at CPU `$BEF2`
  select the expanded character bytes after the `$6D+` source token has chosen
  an entry. Dictionary scans performed at `$BE7C` are lookup traffic and must
  not be mistaken for displayed text.
- Confidence: `code-confirmed` for the record fetch at `$BD30`, token dispatch
  at `$BE6A`, and decoded dictionary fetch at `$BEF2`; `runtime-confirmed` for
  PRG-backed effective reads and dictionary expansion during this dialogue.

### CHR-backed dialogue staging discovered by the corrected token hook

- The corrected `$BE6A` execution hook fired 524 times in the short dialogue
  capture, proving that the hook itself is active.
- During the visible dialogue animation, source values were read repeatedly
  from RAM `$03B0`. They were written at CPU `$C4BB` after PPU data reads in
  the `$C49D-$C4CF` routine.
- `$03B0` lies inside the nominal `$0300-$03BF` PPU-update-buffer range and is
  congruent with the configured value-byte offset. Address alignment alone
  therefore misclassifies these writes as three-byte update entries. The RAM
  range is reused as scratch storage in this rendering mode.
- A valid generic provenance adapter must qualify buffer entries by producer
  path and/or entry header validity, not only by RAM address. For this ROM,
  writes from `$C4BB` must not create text-record provenance.
- The first PRG-backed dictionary token observed in this run was `$D7` at CPU
  `$8501` (frame 418), which expanded through dictionary address `$8AEE`.
  This is a real token-to-dictionary link, but its semantic association with
  the NPC sentence is not yet established.
- A follow-up trace captured one selector value (`$00BF`) at CPU `$C433`, then
  42 PPU read windows beginning at `$1397` and advancing one byte at a time.
  Each window copies eight bytes to `$03B0-$03B7`; consecutive windows overlap
  by seven bytes. The first byte from each window forms the compressed token
  stream `6D 19 E7 22 15 19 11 D7 ... FC` consumed by the text decoder.
- That exact stream occurs once in the ROM at physical CHR offset `$3397`
  (file offset `$B3A7`). PPU `$1397` therefore mapped to physical CHR `$3397`
  in this run, selecting the second 8 KiB CHR bank.
- The record begins immediately after an `$FC` at CHR `$3396` and reaches its
  own `$FC` at CHR `$33C0`, giving the half-open candidate range
  `$3397-$33C1` (42 bytes). This is now a static extraction candidate rather
  than a PRG record.
- Confidence: `runtime-confirmed` for `$03B0-$03B7` as the overlapping CHR text
  window, the `$C4BB` producer, and the PPU `$1397+` sequence;
  `cross-validated` for the physical CHR `$3397-$33C0` token stream.

### Static expansion of the first CHR dialogue record

- The PRG dictionary at `$0858-$0B20` contains exactly 123 `$FA`-terminated
  entries, matching source tokens `$6D-$E7` when `$6D` is subtracted.
- Expanding CHR `$3397-$33C1` produces 48 bytes from 42 source tokens. Each
  exported token retains its CHR offset, original value, dictionary index, and
  expansion rather than losing provenance in a flattened string.
- The flattened byte stream is:
  `55 62 19 24 F8 22 15 19 11 0F F8 5F 1C F8 10 19 1E 30 FE 28 19 5F 35 15 1F 5F 0A 0B 1F 11 32 0F F8 2F 0B FE 28 38 1C 0E 32 18 F8 5F F2 2F 61 FC`.
- With only previously evidenced hiragana mappings applied, the review form
  is `<55><62>たびのしたくが できたなら<FE>また わしに あいにくるがよい<FE>まってるぞ <F2>よ<61><FC>`.
  Unknown/control bytes remain explicit; no meaning is assigned to them from
  Japanese semantics alone.
- Confidence: `code-confirmed` for dictionary indexing and delimiters;
  `cross-validated` for the expanded bytes; `semantic-probable` for the review
  transcription until compared with a captured dialogue screenshot.

### Control and punctuation review for CHR `$3397`

- CHR tile inspection identifies `$55` as `＊`, `$62` as `「`, and `$61` as
  `！`. Their repeated dialogue positions agree with the bitmaps.
- `$F8` combines with the preceding kana as the voiced-sound modifier. The
  review renderer uses a combining dakuten and Unicode normalization, while
  the raw byte remains independently represented in the character map.
- `$FE` branches to the `$BD4A` line-advance routine, which advances the text
  destination by `$40` Nametable bytes (two tile rows). It renders as a line
  break in review output.
- `$F2` saves the current decoder pointer in `$9B/$9C`, changes `$99/$9A` to
  RAM `$00B5`, and later returns through the normal dictionary-termination
  path. A screenshot with the one-character player name `あ` shows `あ` at
  exactly this position in `まっておるぞ あ よ！`, confirming a fixed-width
  player-name insertion field.
- `$FC` is retained as `<END>` and follows the record-ending control path.
- The generated review contains no unmapped bytes and currently reads:
  `＊「たびのしたくが できたなら` / `また わしに あいにくるがよい` /
  `まっておるぞ {PLAYER_NAME}よ！<END>`.
- Confidence: `cross-validated` for `$55/$61/$62/$F8`;
  `code-confirmed` for `$FE/$FC` behavior and `$F2` pointer switching;
  `runtime-confirmed` for interpreting RAM `$00B5` as the player name and for
  the complete three-line transcription.

### Batch CHR dialogue catalog

- The reproducible catalog pass analyzes all 547 bounded `$FC`-terminated CHR
  records instead of selecting only known dialogue ranges.
- Every entry has a stable offset-derived ID, physical CHR/file range, raw and
  expanded bytes, decoded review text, unknown-byte list, translation slot,
  and runtime-validation fields.
- The current heuristic ranks 174 records `high`, 130 `medium`, and 243 `low`.
  These labels order review work; they are not assertions that a record is text.
- The confirmed first-NPC record remains `chr-fc-3397`, has no unknown bytes,
  and ranks `high` without a special-case address rule.
- Graphical CHR data can share byte values with dictionary tokens. Therefore
  the catalog assigns every unobserved result `static-candidate` confidence and
  requires runtime source reads to measure false positives.
- An offline runtime matcher now reconstructs the source stream from the first
  byte of each overlapping `$03B0-$03B7` staging window and matches exact raw
  bytes to stable catalog IDs. Replaying the existing validation trace produces
  exactly one hit, `chr-fc-3397`, from 42 runtime bytes. This confirms the
  catalog identity without comparing rendered pixels or Japanese semantics.
- A later lightweight capture produced 78 runtime source bytes. Exact catalog
  matching accounts for all of them: one `chr-fc-3397` hit and two
  `chr-fc-215b` hits. The latter decodes as
  `そのほうこうには だれも いない<4F><END>` and is now runtime-confirmed
  text despite having ranked only `medium` statically. The duplicate means the
  player attempted to speak twice in a direction without an NPC; it is two
  occurrences but only one distinct record.
- A second lightweight capture produced 166 runtime source bytes and all 166
  were covered by exact catalog matches. It contains five occurrences across
  three IDs: `chr-fc-215b` three times, `chr-fc-35c8` once, and
  `chr-fc-38a7` once. The latter is a 97-byte, seven-line castle tutorial NPC
  dialogue, demonstrating that the same identity mechanism handles both short
  system messages and long multi-line dialogue without PPU screenshot matching.
- Confidence: `runtime-confirmed` for these three record identities and zero
  unmatched bytes in this capture. This validation does not yet assign meaning
  to the remaining unknown controls in their decoded review text.

### First translated dialogue presentation

- `chr-fc-35c8` and `chr-fc-38a7` form the initial short/long presentation
  pair. Both must be runtime-confirmed in the generated catalog before the
  overlay generator accepts them.
- The runtime adapter recognizes exact raw CHR record suffixes from the same
  overlapping staging windows used during validation. Japanese text and its
  translation are presentation data, never identity keys.
- The tracked translation file stores stable IDs and layout but not raw record
  bytes. The exact-ROM bytes are injected from the ignored, locally generated
  validated catalog into a temporary Mesen script.
- Dialogue visibility is independent of controller input. After a match, the
  adapter waits until the dialogue Nametable region becomes stable, then draws
  while it remains stable and hides after a later bulk rewrite. The initial
  implementation treated the long dialogue's final rendering pass as a close;
  the explicit pending/visible phases correct that lifecycle race. This remains
  provisional until both records are visually retested.
- Visual testing exposed that Mesen's Lua HUD uses a fixed Japanese glyph map,
  not a system CJK font. Unsupported simplified characters were silently
  skipped, which looked like missing translation words. Generation now checks
  every presentation character against the actual compiled glyph table;
  canonical translations remain simplified while display pages use supported
  traditional forms.
- Waiting for the full `$FC` record also delayed translation until the final
  Japanese page. The generator now computes each translated record's shortest
  unique raw-byte prefix against all 547 catalog records, so runtime identity
  can be established near the start of the dialogue.
- A first attempt to advance translated pages on a bulk dialogue-region rewrite
  confused the final window close with an internal page change. The native box
  disappeared while a later overlay page remained over the map. Until a
  distinct page-boundary signal is captured, the long prototype record uses
  one complete four-line translation page and treats the first later bulk
  rewrite as the final hide. This is conservative and does not claim exact
  page synchronization.

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

## Logical glyph provenance prototype

- The next diagnostic layer assigns every catalog glyph a zero-based logical
  index while preserving its expanded-byte index and original CHR source
  offset. Modifiers such as `$F8` attach to the preceding glyph and do not
  advance this index; controls and unknown bytes are retained in the catalog
  but are not assumed to occupy a visible cell.
- After a record is identified by its unique CHR prefix, matching glyph values
  written through the confirmed `$0300` PPU queue receive the record ID and
  logical index. The tag is installed only when the queued destination/value
  reaches Nametable RAM. Any unrelated write to that cell clears the old tag.
- Prefix bytes may reach the Nametable before the full unique prefix is known.
  The adapter retains those early queue entries and applies their tags
  retroactively when identity becomes unambiguous.
- Changed shadow state is summarized as logical `[start, endExclusive)` ranges
  for each visible Nametable row. This is the input needed to test translation
  segment selection during dialogue scrolling; it does not yet choose or draw
  a translated segment.
- The first long-dialogue validation identified `chr-fc-38a7` and propagated
  every logical glyph index from 0 through 89. The initial window accumulated
  indices `[0, 46)`. Subsequent overwrite/scroll phases advanced into
  `[46, 64)`, `[64, 79)`, and `[79, 90)` while clearing cells belonging to
  displaced rows. Closing the dialogue produced an empty row set.
- The transient ranges during a scroll are intentionally not assumed to be a
  stable translation page. A presentation adapter should debounce until the
  sourced cells settle, then map the union of visible source intervals to a
  reviewed translation segment. This avoids tying translation changes to the
  controller button that happened to trigger the scroll.
- Confidence: `code-confirmed` for logical-index construction and row grouping;
  `runtime-confirmed` for complete 0-89 propagation, forward range movement,
  overwritten-cell removal, and final clearing in the tested long dialogue.

## Range-driven translation segment selection

- The reviewed translation data now maps contiguous logical source intervals
  to presentation lines. Coverage is validated against each catalog record's
  exact logical glyph count, preventing gaps, overlaps, and stale endpoints.
- Selection uses the greatest currently visible logical glyph index. This
  intentionally ignores a few older tagged cells that may survive briefly
  during a scroll and always chooses the furthest-progressed reviewed segment.
- Presentation is suppressed whenever provenance changes and resumes after
  four stable frames. The policy does not observe controller input and does not
  assume that one source line equals one translated line.
- Confidence: `code-confirmed` for validation and deterministic selection;
  visual behavior remains `semantic-probable` until the segmented overlay is
  exercised through the full long dialogue.

### First visual correction

- The first visual run showed that clearing presentation on every provenance
  change causes flicker during typewriter rendering. It also showed that
  requiring four stable frames can skip a source interval during continuous
  scroll and leave the final interval visible for only a single frame.
- Segment presentation now persists while glyphs within that segment change
  and switches atomically when the newest visible index crosses a reviewed
  boundary. Empty provenance is tolerated for 20 frames to bridge the measured
  11-frame scroll gap; sustained emptiness clears all session state.
- Sustained emptiness resets the active record and logical cursor, allowing the
  same record to be recognized on a later interaction. These corrections
  remain `semantic-probable` pending a repeat visual run.

## External subtitle presentation prototype

- Visual testing demonstrated a structural limitation of drawing translated
  text over the game's dialogue box: Japanese typewriter animation, scrolling,
  and the replacement overlay necessarily compete for the same pixels. Timing
  adjustments can change the symptom but cannot remove that conflict.
- A renderer-independent event router now converts provenance `segment` and
  `reset` events into simple visible/text state. The macOS prototype sends
  that state to a separate AppKit window over JSON lines, leaving the emulated
  256x240 frame untouched.
- The companion window uses the system font, so presentation is no longer
  limited to Mesen's built-in HUD glyph table. PPU provenance and translation
  selection remain independent of this platform-specific view.
- Confidence: `code-confirmed` for event routing through automated tests;
  external-window placement and visual behavior remain `visual-provisional`
  until exercised alongside Mesen.

### External menu layout mode

- The unified runtime script now observes the already-confirmed menu-record ->
  `$0300` update buffer -> Nametable path alongside dialogue glyph provenance.
  It emits only record ID and sourced-cell count; presentation text and layout
  continue to come from the database rather than Lua constants.
- The external router maps all visible menu records to their translated labels
  and composes them with current dialogue translations in one scene. Menu and
  dialogue are no longer mutually exclusive presentation modes.
- The AppKit companion renders position-preserving labels and a dialogue area
  concurrently. This is `code-confirmed` through event-routing tests and
  remains `visual-provisional` pending a combined menu/dialogue run.

## Visible-coverage dialogue alignment

- Visual review showed that the original `[0, 46)` translation interval joined
  two independently presented Japanese sentences. It has been split into
  `[0, 22)` and `[22, 46)`, with one reviewed Chinese sentence per interval.
- Runtime coverage snapshots count current sourced Nametable cells for every
  alignment interval. The external router now derives each scene only from the
  current snapshot: an interval is included at 25% coverage and omitted below
  it. It does not retain a previously displayed interval through a handoff.
- Same-value rewrites at the same Nametable address now preserve both menu and
  dialogue provenance. This prevents ordinary window redraws from erasing the
  source identity even though the visible tile did not change.
- Runtime validation showed that dialogue scrolling moves existing tile rows
  without rereading their source bytes. The prototype now recognizes write
  batches with at least three matching tiles at a 32-tile row displacement and
  migrates their provenance. A `(recordId, glyphIndex)` pair is kept at only
  one current cell, preventing old and new rows from both contributing.
- Multiple active intervals are rendered in source order. This implements the
  proposed Nametable-visible-position -> original interval -> translated unit
  mapping without proportionally truncating Chinese characters.
- Confidence: `code-confirmed` for interval validation, current-state coverage
  routing, and menu/dialogue composition; visual result remains
  `visual-provisional` pending another long-dialogue run.

### Per-label menu visibility

- Record-level menu visibility was too coarse: a partially covered main menu
  caused all eight translated labels to remain beside a higher status window.
- Each presentation label is now mapped from its database `clear` rectangle to
  a Nametable tile region. Runtime group events report sourced-cell counts per
  label, and the scene contains only labels whose own region remains present.
- Confidence: `code-confirmed` through routing tests; the label-region behavior
  is `runtime-confirmed` for the reviewed main-menu/status-window run.

### PPU-coordinate translation mirror

- The external AppKit view now uses a `256x240` logical canvas with a default
  `768x720` content size and fixed NES aspect ratio. Both short labels and
  dialogue boxes are placed from database PPU pixel rectangles and relaid out
  on resize.
- Directly comparing those rectangles with physical Nametable offsets lost the
  first command label after map scrolling. Runtime mapping now combines the
  logical PPU write address with `ppu.tmpVideoRamAddr` and `ppu.xScroll` to
  obtain the tile's current screen position before assigning label ownership.
- A visual run confirmed all eight main-command translations and correct
  higher-window coverage after the viewport correction. Confidence:
  `runtime-confirmed` for this Dragon Quest scene.

### Visible translation snapshot

- The Python projection now emits one renderer-independent
  `visible-translation-snapshot`. Short labels and dialogue intervals share a
  single item representation containing PPU bounds and current coverage.
- The AppKit mirror has no menu/dialogue rendering branches; it scales and
  draws the snapshot items uniformly. Runtime provenance remains responsible
  for deciding which items exist.
- When several dialogue units share one container, the snapshot assigns them
  ordered, non-overlapping PPU sub-rectangles before rendering. This keeps the
  mirror generic while preventing independent text fields from occupying the
  same full dialogue box.
- Confidence: `runtime-confirmed` for the reviewed combined menu/dialogue run;
  48 automated tests cover snapshot composition, normalized text units, and
  non-overlapping placement.
- Menu labels and dialogue segments are normalized to one internal `TextUnit`
  model before snapshot projection. This removes their different database
  shapes from presentation without claiming their runtime provenance
  collectors are already interchangeable.
- Current presentation state is one map keyed by normalized `unitId`. Menu and
  dialogue adapters replace their matching entries from each complete coverage
  event, so the snapshot retains no separate mode or stale subtitle fallback.
  Confidence: `code-confirmed` by the 48 routing tests.
- Snapshots now report `appeared`, `updated`, and `disappeared` unit IDs as a
  renderer-optional delta. Tests cover all three transitions; this is
  diagnostic metadata and does not alter current PPU-derived visibility.

### Snapshot capture and replay

- Runtime snapshots can optionally be written as UTF-8 JSONL while Mesen is
  running. Capture works with or without the external mirror and stores no ROM
  bytes.
- A standalone replay command validates the trace and feeds it back to the
  same companion using recorded frame gaps, with configurable FPS and speed.
  This makes rendering and lifecycle regressions repeatable without replaying
  the game interaction.
- The end-to-end validation capture contained 186 snapshots spanning frames
  17547-19053, including the main menu, status window, and reviewed long
  dialogue. Its deltas contained 47 appearances, 106 updates, and 47
  disappearances; the trace ended with no visible translation.
- The same trace was replayed through the AppKit companion without Mesen. The
  user confirmed that menu, status, dialogue transitions, overlap handling,
  and final clearing matched the live run. Confidence: `runtime-confirmed`;
  50 automated tests additionally cover validation, serialization fidelity,
  and frame-timed replay.

### Automated snapshot audit

- A standalone auditor checks the renderer-independent trace for duplicate
  units, invalid/out-of-viewport rectangles, inconsistent coverage, incorrect
  deltas, overlap starts, quick reappearance, long-lived units, and a trace
  ending before translations clear.
- The validated 186-snapshot trace produced zero errors. Four warnings marked
  the start of expected overlap while the strength window covered the lower
  main-menu labels at frames 18248-18249; sustained overlap is intentionally
  reported only once per pair.
- Confidence: `code-confirmed`; 52 automated tests cover valid traces and the
  major error/warning classes. The real-trace result agrees with the earlier
  successful visual replay.

### Snapshot lifecycle regression fixture

- A six-snapshot, ROM-free JSONL fixture fixes the expected transition order:
  menu, higher replacement window, restored menu, first dialogue unit, two
  ordered dialogue units, then an empty scene.
- The fixture is loaded through the production trace parser and must pass the
  production auditor with zero errors and zero warnings. Confidence:
  `code-confirmed`; the full suite now contains 53 tests.

### Normalized TextUnit contract

- `PpuBounds`, `TextUnit`, and database normalization now live in a standalone
  module rather than the Dragon Quest glyph-provenance command.
- Each unit explicitly records whether it is a short label or dialogue unit,
  with a label source index or dialogue source interval. The router no longer
  parses unit ID strings to recover source type or index.
- This is a database/runtime boundary, not scene recognition. Confidence:
  `code-confirmed`; all 53 tests pass with unchanged snapshot output.

### Unified visibility update contract

- Both current runtime adapters now resolve their native events to a complete
  scoped `VisibilityUpdate` containing normalized unit IDs and visible counts.
- The state machine atomically replaces only that scope and rejects unknown
  scopes or units belonging to another scope. It no longer understands menu
  label indices or dialogue source ranges.
- Confidence: `code-confirmed`; 54 tests include direct generic visibility
  updates, scope isolation, the lifecycle fixture, and existing runtime event
  adapters.
