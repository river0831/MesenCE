# Runtime translation message model

The translation runtime separates immutable per-ROM knowledge from transient
emulator state.

## Static translation-pack records

A `TranslationRecord` identifies a reusable source template. It may declare
translated segments and parameter slots, but never stores a runtime parameter
value or a message lifecycle ID.

## Runtime message instances

Each execution of a record creates a new `MessageInstance`, even if the same
NPC, menu, or source address was used previously. An instance owns:

- an ID unique to the emulator session;
- its static record ID;
- start, last-activity, and optional end frames;
- an ordered list of observed source spans;
- runtime parameter instances;
- logical character instances.

Source spans form an execution trace. Non-contiguous reads, pointer jumps, and
shared suffixes remain separate spans instead of being widened into one ROM
address interval.

## Runtime parameters

A static template may declare a slot such as `ITEM`. Each message instance
resolves that slot independently. The resolved item ID, rendered Japanese text,
and translated value are runtime data and do not modify the translation pack.

If a parameter's semantic type is unknown, the runtime may retain an anonymous
slot such as `PARAM_1`. Characters emitted by the parameter keep the parent
message instance ID and additionally name their parameter slot.

## Logical characters and physical tiles

A `LogicalCharacter` has an identity derived from its message instance and
logical index. It may expand into one or more physical glyph components. This
allows a base kana and a separate dakuten tile to share one character identity.

Nametable cells should eventually store the logical character ID rather than
only a record ID or tile value. Tile values validate propagation but do not
define semantic identity.

## Visibility lifecycle

PPU writes update dirty cell state. Translation visibility is committed from
the final end-of-frame Nametable snapshot, optionally after a short stability
window. Intermediate writes within a frame do not create or close message
instances by themselves.
