# Implementations

Who produces and reads byterefs tables, and at which version. Listed so the
specification can be measured against them; none of them defines it.

raad.virtualize writes `byterefs/0.1` (since mdsumner/raad.virtualize#62,
2026-11-03); zaro reads it and, during the transition, `mdim-refs/0.2`
(decision 0003). The implementations that the
starting draft (mdim-refs/0.2) was worked out against are listed in
[BRIEF.md](BRIEF.md) section 9.

| Implementation | Language | Role | byterefs version | Notes |
|---|---|---|---|---|
| [raad.virtualize](https://github.com/mdsumner/raad.virtualize) | R, Python | producer: scans sources, holds the SQLite working store, writes the Parquet export, renders kerchunk, Icechunk, mdim VRT and STAC | byterefs/0.1 (writes, with `meta.default_target`) | published drafts on source.coop `ausantarctic-scratch` |
| wxylib/core `wxy-refs` | Rust | reader: zarrs storage over the Parquet export; writes Icechunk | mdim-refs/0.2 | oracle-tested against wxylib/fixtures |
| [ArrIR](https://github.com/charles-turner-bot/arrir) `arrir-layout` | Rust | reader: storage-layout binding of the three-file Parquet export | byterefs/0.1 (design) | not yet released |
| [zaro](https://github.com/hypertidy/zaro) `byterefs://` (alias `mdimrefs://`) | R | reader: serves Zarr v2 keys from the SQLite store | byterefs/0.1 and mdim-refs/0.2 | placement-first chunk lookup, batched (hypertidy/zaro#19); `arrays.codec` as a V3 codec chain or the V2 form (0007); whole-object rows (0008); applies `meta.default_target` (hypertidy/zaro#15); reads SQLite, not the Parquet export |

To add an implementation, open a pull request that adds a row.
