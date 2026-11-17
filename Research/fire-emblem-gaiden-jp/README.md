# Fire Emblem Gaiden (Japan) text extraction

The deep extraction output is under `generated/extracted-text/`:

- `text-segments.json`: every explicitly decoded source string, without guessing message boundaries.
- `message-records.json`: conservative message/menu records with controls such as newline, wait, face, name, and template variables preserved.
- `message-records.md`: human-readable review copy.
- `character-table.json`: single- and multi-byte character mappings, including dakuten/handakuten and `%0`–`%3` template slots.

Regenerate with:

```sh
python3 Tools/NesTranslation/fire_emblem_gaiden_text.py \
  --source-dir /path/to/fe2/src \
  --output-dir Research/fire-emblem-gaiden-jp/generated/extracted-text \
  --rom "test_roms/Fire Emblem Gaiden (Japan).nes"
```

The extraction uses the decoded text ranges in the public `minirop/fe2`
disassembly. The local ROM has the same CHR data but a different PRG/full-ROM
checksum from that project's reproducible build, so runtime validation remains
necessary before treating source labels as local-ROM addresses.
