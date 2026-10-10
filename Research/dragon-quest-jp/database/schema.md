# Dragon Quest PoC database contract

This database is intentionally bound to one exact ROM. All PRG ranges use a
zero-based physical PRG offset and an exclusive end. `rawHex` includes every
byte in the range, including unknown/control bytes and the final terminator.

Record IDs are stable identities. Runtime matching uses `prgRange`; Japanese
or translated strings are never used as keys.

Confidence values used by this project are `visual-provisional`,
`semantic-probable`, `cross-validated`, `runtime-confirmed`, and
`code-confirmed`.
