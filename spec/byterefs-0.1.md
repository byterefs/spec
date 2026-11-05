# byterefs/0.1: byte-reference table

Status: draft. Not normative until the v0.1 gate in [BRIEF.md](../BRIEF.md)
section 7 is met. This text starts as the mdim-refs/0.2 draft
([wxylib/design `specs/mdim-refs-0.2.md`](https://github.com/wxylib/design/blob/main/specs/mdim-refs-0.2.md)),
as decision [0002](../decisions/0002-start-from-mdim-refs-0.2.md) says.
Every departure from that text is listed in
[Changes from mdim-refs/0.2](#changes-from-mdim-refs02), with the decision
that made it.

Column names follow GDAL's raw block information (`GetRawBlockInfo`, and the
planned `gdal mdim chunk-info` subcommand). The sections on writers, readers
and validation are informative: they record where the text was tested, not
what it requires. Implementations are listed in
[IMPLEMENTATIONS.md](../IMPLEMENTATIONS.md).

## Model

Three layers, each held once:

1. **Physical**: for each source and each array in it, the byte range of every
   chunk, keyed on the chunk's position *within the source*. This is the row
   block-info emits when run on one source file. It holds no time, no dataset
   and no remapping, so a source is scanned once and a rescan is an in-place
   upsert.
2. **Plan**: where each source's slab sits in the global array. This is the
   `<Source>` list of a `gdal mdim mosaic` VRT (SourceSlab and DestSlab),
   copied into the store so that the table stands alone outside GDAL.
3. **View**: the global chunk index, `refs_<array>`, computed from 1 and 2.
   Its rows are what block-info would emit if run on the mosaic as one array.

Every published form (kerchunk Parquet, Icechunk, a GDAL OGR layer, a zaro
store) is a projection of the view plus the `arrays` metadata.

## Tables

One SQLite file per dataset. Names `meta`, `sources`, `arrays`, `placements`,
`remap` and the prefix `refs_` are reserved.

| Table | Key | Columns |
|---|---|---|
| `meta` | `key` | `value`. Required: `format_version` = `byterefs/0.1`. Optional: `default_target` (see Rules), `dataset` (bowerbird source id), `plan` (VRT URI the placements came from), `coord_attrs` |
| `sources` | `source_id` | `source` TEXT UNIQUE, `size` BIGINT, `mtime` BIGINT, `etag` TEXT |
| `arrays` | `array` | `kind` (`data`, `coord`), `storage` (`referenced`, `inline`, `affine`), `dims`, `shape`, `chunks` (JSON), `dtype` (numpy, e.g. `<i2`), `fill` (text), `codec` (JSON `{compressor, filters}`, Zarr v2 ids), `attrs` (JSON, CF), `affine` (JSON `{start, step}`), `values` (BLOB) |
| `<array>` | `(source_id, dim_0..dim_{n-1})` | `present` INTEGER, `offset` BIGINT, `size` BIGINT, `info` TEXT, `data` BLOB |
| `placements` | `(array, dest)` | `source_id`, `source_array`, `src_offset`, `count`, `dest` (each a JSON array, one integer per global dimension: SourceSlab offset, SourceSlab count, DestSlab offset) |
| `remap` | `(target, prefix)` | `replacement` |
| `refs_<array>` (view) | `dim_0..dim_{n-1}` | `present`, `path`, `offset`, `size`, `info`, `data` |

All chunk tables are `WITHOUT ROWID`. `shape` in `arrays` is the global shape
from the plan; `chunks`, `dtype` and `codec` describe the sources.

## Rules

- **Source rule.** `sources.source` is the URI opened at scan time, verbatim
  (`/rdsi/...`, `/vsicurl/https://...`, `/vsis3/...`). Offsets are bound to it.
  Preliminary and final versions of a granule are distinct sources; which one a
  dataset uses is decided by the plan.
- **Remap at publish.** A published path is the source with the longest
  matching `remap.prefix` for the chosen `target` replaced; a source that no
  rule matches is used verbatim. Remapping is never written into `sources`.
  The rules travel with the published table, and only prefix rules are
  allowed (no templates). This replaces the three ad hoc rewrites (Parquet
  edits, `rename_paths`, `ref_prefix`).
- **Default target.** `meta.default_target` names the target a reader
  applies when it is not told one; the empty string means verbatim. A
  store meant for public use SHOULD name a default target under which
  every source resolves without site access.
- **A rule asserts byte identity.** A remap rule claims that the bytes at
  the replacement are the bytes that were scanned. A producer SHOULD check
  a sample of chunks through each target it publishes. `size` holds across
  targets; `mtime` and `etag` hold for the verbatim source only.
- **No confidentiality.** The format does not hide a local root. A producer
  that must not disclose one publishes a copy of the store with a target
  applied to `sources.source` and that target's rules dropped.
- **Presence.** Block-info's three states: present and referenced
  (`present=1`, `offset` and `size` set), present and inline (`present=1`,
  `offset` NULL, `data` set), absent (`present=0`; readers use `fill`).
- **Within-source keys carry the global rank.** A source of lower rank than
  the array (a 2D tile placed in a 3D stack, VRT `SourceTranspose -1,0,1`)
  has key 0 on each axis its placement adds. A placement may add leading
  axes; it may not permute the source's own axes.
- **`info`** is the block-info text form, `KEY=VALUE` pairs joined by `; `
  (`COMPRESSION=DEFLATE; FILTER=SHUFFLE; ENDIANNESS=LITTLE`). Readers may
  also accept the JSON list osgeo.gdal's `GetInfo()` returns. The mapping
  to codecs is in "Codec mapping" below.
- **Byte columns are BIGINT**, so OGR and Arrow read them as 64-bit.
- **One codec per array.** All present chunks of an array carry the same
  `info` (compared as parsed pairs, not raw strings), across every
  ingest, not only within one scan. A source whose chunks disagree (a filter skipped on some chunks)
  cannot join the array; ingest fails rather than writing a mixed array.
- **Chunk-aligned plan.** Each placement has step 1, `src_offset` and `dest`
  divisible by `chunks`, and `dest + count` divisible by `chunks` unless it
  reaches the end of the global axis. Otherwise the mosaic has no single
  regular chunk grid and cannot be virtualised.
- **Coordinates** come from the plan (`InlineValues` as `values`,
  `RegularlySpacedValues` as `affine`). Their CF attributes come from the
  source scan, because the mosaic VRT drops some (time `units` for OISST).
- **Publish in DELETE journal mode** (checkpoint, then `journal_mode=DELETE`),
  so a read-only remote copy opens without WAL sidecars.

## The view

For array `a` with chunk shape `c`, a row of `refs_a` is a row of chunk table
`a` joined to its placement, with

```
dim_i(global) = dim_i(source) - src_offset_i / c_i + dest_i / c_i
```

restricted to source chunks inside the slab, and `path` the verbatim source.
`mr_view_sql(con, a, target)` writes the same query with remapped paths. The
columns are exactly the block-info layer: `dim_0..dim_{n-1}`, `present`,
`path`, `offset`, `size`, `info`, plus `data` for inline chunks.

**One chunk by global key.** Filtering the view on its computed keys scans
every row. The per-chunk read path joins from the placement instead: the
placement whose `dest` slab holds the key, then

```
dim_i(source) = dim_i(global) - dest_i / c_i + src_offset_i / c_i
```

looked up by the chunk table's primary key (`mr_chunk_sql()`). Measured
under 1 ms at about 1M chunks, against 0.9 to 1.9 s through the view
(design m15).

## Codec mapping

| `info` | Zarr v2 | Zarr v3 |
|---|---|---|
| `COMPRESSION=DEFLATE` | compressor `zlib` | `numcodecs.zlib` |
| `COMPRESSION=ZSTD` | compressor `zstd` | `zstd` |
| `FILTER=SHUFFLE` | filter `shuffle`, `elementsize` = item size | `numcodecs.shuffle` |
| `PREDICTOR=2` (TIFF) | filter `imagecodecs_delta`, `axis` -1, `dist` 1 | `HorizontalDeltaCodec`, ahead of `bytes` |
| `ENDIANNESS=LITTLE` or `BIG` | must agree with `dtype` | `bytes` endian |

Anything else (`PREDICTOR=3`, other filters) is not mapped and stops ingest.

## Writers and readers

| Form | Route | State |
|---|---|---|
| GDAL vector (OGR) | open the SQLite file; `refs_<array>` is a layer | works with stock GDAL |
| kerchunk Parquet (D) | `mr_write_kerchunk_parquet()` -> `blocklist::write_kerchunk_parquet()` | works; read by GDAL as `ZARR:"/vsikerchunk_parquet_ref/{dir}"` |
| zaro | `zaro("mdimrefs://store.sqlite", target = "public")` | works; serves Zarr v2 keys from the view |
| Icechunk (C) | bulk-load the view rows as virtual chunk refs | not started |
| block-info producer | `blockinfo_scan.py` (stock `GetRawBlockInfo`) now; `gdal mdim get-refs` output is the same rows | Python only; no R binding of `GetRawBlockInfo` exists |

## Mapping from earlier stores

| Concept | raad.virtualize | aad-filelist 0.1 | block-info | 0.2 |
|---|---|---|---|---|
| file | `files(file_id, source)` | `sources(file_id, access, public)` | `path` per row | `sources(source_id, source, size, mtime, etag)` |
| chunk key | `file_id, idx0..` (within file) | `idx0..` (global) | `dim_0..` | `source_id, dim_0..` (within source) + view `dim_0..` (global) |
| bytes | `offset, size` INTEGER | `offset, size` INTEGER | `offset, size` Integer64 | `offset, size` BIGINT |
| per-chunk codec | none | `info` | `info` | `info` |
| inline | none | `data` BLOB | planned | `data` BLOB |
| array metadata | none (from the VRT) | `arrays` | layer metadata | `arrays`, global shape from the plan |
| placement | in the projection code | implicit in global `idx` | n/a | `placements` (from the VRT) |
| public paths | projection code | `public` column | n/a | `remap` |

## Validation (2026-10-03)

- Block-info rows from stock GDAL 3.13 `GetRawBlockInfo` on the NOAA S3 copies
  equal the v0.1 store rows for the same files: 120 of 120 rows (30 days, four
  arrays) match on offset and size, so the /rdsi mirror and S3 agree there.
- 30 days (September 1981): `gdal mdim mosaic` over `/vsicurl/` -> scan ->
  store -> kerchunk Parquet. Day 30 read through GDAL from the kerchunk store
  and through zaro from the table both equal GDAL reading the source netCDF.
- Full store: the 16,387-source v0.1 store migrated in under 10 s (14 MB). The
  `refs_sst` view returns 16,387 rows in 0.14 s; kerchunk Parquet for four
  arrays writes in 1.3 s. Days 1981-09-01, 1995-03-17, 2026-06-01 and
  2026-07-13 (preliminary) read identically through GDAL-on-kerchunk,
  zaro-on-table and GDAL-on-source.
- Not tested: bluelink (NCI THREDDS was not reachable from the build
  environment), Icechunk, multi-chunk-per-source arrays, absent and inline
  chunks against real data.

## Open questions

1. The view filters on computed columns, so a single-chunk lookup through
   it scans the array's rows. Answered for point lookups by the
   placement-first join in "The view"; materialising `refs_<array>` as a
   keyed table remains an option for SQL-only readers that filter ranges
   through the view.
2. Placements duplicate the VRT. The alternative is to keep the VRT as the only
   plan and compute the view in code; that loses SQL-only readers.
3. Home for `R/mdimrefs.R`: raad.virtualize (store) with the writer staying in
   blocklist, or a small package of its own.
4. **Proposed: per-axis chunk edges** (from wxylib design m10, overlapping
   COG mosaics). 0.2 assumes one regular chunk grid per array, so a mosaic
   whose winning tiles have unequal sizes cannot be virtualised. The
   proposal: an optional `chunk_edges` column in `arrays` (JSON, one list
   of cumulative edges per dimension, the Zarr `rectilinear` grid of
   zarr-extensions), with `chunks` kept as the source chunk shape; when
   present, the view's global keys index those edges instead of
   `dest_i / c_i`, and the chunk-aligned plan rule becomes "each placement
   starts and ends on an edge". Readers that do not know the column refuse
   the array rather than misread it. To be agreed here before any writer
   or reader emits it; it is not a wxylib extension.
5. **Parquet export layout.** The export (`refs_<array>.parquet` plus
   `arrays.json`, plus `sources.parquet`) is the flat refs store that
   tables are harvested into and virtual indexes are rendered from. The
   SQLite file is the producer's working encoding; the export is the
   published one and the input every renderer should take (design m15).
   Its layout is not fixed: one self-describing Parquet file with `meta`,
   `arrays` and `remap` in key-value metadata is the likely end. Rows
   should be sorted by the dims and split into row groups along `dim_0`
   so readers can prune; `path` may be dictionary-encoded (required at
   tens of millions of rows).

## Changes from mdim-refs/0.2

| # | Change | Decision |
|---|---|---|
| 1 | Title, status and opening paragraphs rewritten for this repository; the wxylib/design notes removed | editorial |
| 2 | `meta.format_version` is `byterefs/0.1` instead of `mdim-refs/0.2` | [0003](../decisions/0003-format-identifier.md) |
| 3 | Remap: rules travel with the published table, prefix rules only, `meta.default_target`, byte-identity and no-confidentiality statements | [0004](../decisions/0004-source-paths-and-remap.md) |

No other rule, table or column has changed. Relative paths are still open (0004). In particular, this text still
describes SQLite as the store; making the Parquet export the normative
published encoding (decision 0001, brief question 7) is a later change with
its own record.
