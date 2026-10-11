# Dragon Quest PoC database contract

This database is intentionally bound to one exact ROM. All PRG ranges use a
zero-based physical PRG offset and an exclusive end. `rawHex` includes every
byte in the range, including unknown/control bytes and the final terminator.

Record IDs are stable identities. Runtime matching uses `prgRange`; Japanese
or translated strings are never used as keys.

An optional `deactivation.dismissInputMask` is an exact-ROM runtime rule. It
only applies while that record is active; a matching controller press emits a
hide event. Such rules require a separately recorded confidence value and must
be verified against a visible close action.

Confidence values used by this project are `visual-provisional`,
`semantic-probable`, `cross-validated`, `runtime-confirmed`, and
`code-confirmed`.
