# Five-game extraction workspace

This workspace tracks the first-pass extraction requested for the five local
Japanese NES ROMs other than Dragon Quest.  A generated CHR atlas is evidence
about graphics present in the cartridge; it is not, by itself, a decoded text
catalog.

| Game | Mapper | PRG | CHR | Static atlas | Text status |
|---|---:|---:|---:|---|---|
| Contra (Japan) | 23 | 128 KiB | 128 KiB | 16 banks / 8192 tiles | Latin/digit font located; text boundaries and encoding unconfirmed |
| Fire Emblem Gaiden (Japan) | 10 | 256 KiB | 128 KiB | 16 banks / 8192 tiles | Kana font located; compressed/tokenized text format unresolved |
| Final Fantasy (Japan) | 1 | 256 KiB | CHR-RAM | Requires runtime PPU capture | Font is uploaded from PRG at runtime; no CHR-ROM section exists |
| Ninja Ryuuken Den III (Japan) | 4 | 128 KiB | 128 KiB | 16 banks / 8192 tiles | Kana font located; text boundaries and encoding unconfirmed |
| Portopia Renzoku Satsujin Jiken (Japan) | 0 | 32 KiB | 8 KiB | 1 bank / 512 tiles | Plain candidate text area located; control bytes and voiced glyphs need decoding |

## Output layout

For CHR-ROM games, full atlases and lossless tile manifests are under:

```text
Research/<game>/generated/chr-atlas/
  chr-bank-N.png
  chr-tiles.json
```

Each JSON tile record contains the CHR bank, pattern table, tile index, CHR
offset, exact 16-byte pattern, SHA-256 pattern identity, blank status, and an
optional reviewed character label.

## Accuracy rule for text extraction

Raw runs of bytes that happen to fall in a font's tile-number range are not
accepted as text.  NES program instructions, lookup tables, maps, animation
data, and compressed graphics frequently contain the same values.  A text
record is promoted only after its character mapping, boundary/control format,
and at least one runtime rendering path are supported by evidence.  Chinese
translation begins from those promoted records; uncertain byte runs remain
candidate evidence rather than fabricated dialogue.

## Next extraction requirements

- Contra: identify string pointer tables and terminators; separate English UI
  strings from code/data collisions.
- Fire Emblem Gaiden: identify the dialogue decompressor/token dictionary and
  map its logical codes to the font.
- Final Fantasy: capture the runtime CHR-RAM font, then locate the PRG font
  source and dialogue decoder.
- Ninja Ryuuken Den III: locate cutscene text pointer tables and control codes.
- Portopia: finish the visible kana/voicing map and validate the apparent
  `FF`/`FE`/`FC` spacing, line-break, and record-boundary roles at runtime.
