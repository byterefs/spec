# Implementations

Who produces and reads byterefs tables, and at which version. Listed so the
specification can be measured against them; none of them defines it.

No implementation writes `byterefs/0.1` yet; the rows below target it and
read `mdim-refs/0.2` during the transition (decision 0003). The implementations that the
starting draft (mdim-refs/0.2) was worked out against are listed in
[BRIEF.md](BRIEF.md) section 9.

| Implementation | Language | Role | byterefs version | Notes |
|---|---|---|---|---|
| [raad.virtualize](https://github.com/mdsumner/raad.virtualize) | R, Python | producer: scans sources, holds the SQLite working store, writes the Parquet export, renders kerchunk, Icechunk, mdim VRT and STAC | mdim-refs/0.2; byterefs/0.1 planned | published drafts on source.coop `ausantarctic-scratch` |
| wxylib/core `wxy-refs` | Rust | reader: zarrs storage over the Parquet export; writes Icechunk | mdim-refs/0.2 | oracle-tested against wxylib/fixtures |
| [ArrIR](https://github.com/charles-turner-bot/arrir) `arrir-layout` | Rust | reader: storage-layout binding of the three-file Parquet export | byterefs/0.1 (design) | not yet released |
| [zaro](https://github.com/hypertidy/zaro) `mdimrefs://` | R | reader: serves Zarr v2 keys from the SQLite store | mdim-refs/0.2 | reads SQLite, not the Parquet export |

To add an implementation, open a pull request that adds a row.
