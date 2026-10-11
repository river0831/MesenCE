# Dragon Quest PoC database contract

This database is intentionally bound to one exact ROM. All PRG ranges use a
zero-based physical PRG offset and an exclusive end. `rawHex` includes every
byte in the range, including unknown/control bytes and the final terminator.

Record IDs are stable identities. Runtime matching uses `prgRange`; Japanese
or translated strings are never used as keys.

The exact-ROM `runtime` object declares the CPU address base used to map
physical PRG offsets and the internal input-state address verified for this
game. These values are injected into runtime adapters; generic tools must not
hard-code them.

An optional `presentation` describes how a display adapter renders a record.
The initial `label-overlay` mode contains one or more labels with display text,
native-screen coordinates, and a positive `clear` rectangle. `translation`
remains the canonical simplified-Chinese meaning; presentation text may use a
font-compatible glyph variant until the bitmap-font renderer is implemented.

An optional `deactivation.dismissInputMask` is an exact-ROM runtime rule. It
only applies while that record is active; a matching controller press emits a
hide event. When `deactivation.returnToRecordId` is present, the same input
restores that underlying record with a replace event instead. Such rules
require a separately recorded confidence value and must be verified against a
visible close action.

Confidence values used by this project are `visual-provisional`,
`semantic-probable`, `cross-validated`, `runtime-confirmed`, and
`code-confirmed`.
