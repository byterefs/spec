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
| `arrays` | `array` | `kind` (`data`, `coord`), `storage` (`referenced`, `inline`, `affine`), `dims`, `shape`, `chunks` (JSON), `dtype` (numpy, e.g. `<i2`), `fill` (text), `codec` (JSON, a Zarr V3 codec chain; see Rules), `attrs` (JSON, CF), `affine` (JSON `{start, step}`), `values` (BLOB) |
| `<array>` | `(source_id, dim_0..dim_{n-1})` | `present` INTEGER, `offset` BIGINT, `size` BIGINT, `info` TEXT, `data` BLOB |
| `placements` | `(array, dest)` | `source_id`, `source_array` (see [Source arrays](#source-arrays)), `src_offset`, `count`, `dest` (each a JSON array, one integer per global dimension: SourceSlab offset, SourceSlab count, DestSlab offset) |
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
  a sample of chunks through each target it publishes. `size`, where it
  is set, holds across targets; `mtime` and `etag` hold for the verbatim
  source only.
- **No confidentiality.** The format does not hide a local root. A producer
  that must not disclose one publishes a copy of the store with a target
  applied to `sources.source` and that target's rules dropped.
- **Presence.** Block-info's three states, plus one: present and
  referenced (`present=1`, `offset` and `size` set), present and inline
  (`present=1`, `offset` NULL, `data` set), absent (`present=0`; readers
  use `fill`), and present as a whole object (`present=1`, `offset` 0,
  `size` NULL: the whole object at `path`, length not recorded; a reader
  fetches the whole object).
- **Unknown sizes.** `size` NULL with any `offset` other than 0 is
  invalid. A writer never stores a placeholder or sentinel as `size`: if a
  source format holds one in place of a real length, the converter writes
  NULL. A writer SHOULD record sizes it knows; a size from an object
  listing is good enough. A writer of a form that needs a length (for
  example Icechunk virtual chunk references) measures the object or
  refuses the row; it never supplies a value of its own.
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
- **Codec chain.** `arrays.codec` is a JSON array of codec objects
  `{"name": ..., "configuration": {...}}` in encode order, as in the
  `codecs` member of Zarr V3 array metadata. It describes how the stored
  bytes of every present, referenced chunk decode to the chunk's values.
  The chain holds any array-to-array codecs first, then exactly one
  array-to-bytes codec, then any bytes-to-bytes codecs.
  `sharding_indexed` is not allowed in it. The `bytes` codec's `endian`
  agrees with the byte order of `dtype` (and may be left out for a
  one-byte `dtype`). Names are those of Zarr V3 and its registered
  extensions; a reader that does not know a name refuses the array.
  During byterefs/0.x `arrays.codec` may instead hold the Zarr V2 form
  `{compressor, filters}`; readers tell the forms apart by JSON type (an
  array is a V3 chain, an object is the V2 form). Writers SHOULD write
  the V3 chain; readers MUST accept both.
- **Sharded sources.** A sharded Zarr V3 source is chunked at its inner
  chunks: one row per inner chunk, with `path` the shard object, `offset`
  and `size` from the shard index, and the chunk key the inner chunk's
  position in the source's grid of inner chunks. `arrays.chunks` is the
  inner chunk shape and `arrays.codec` the inner codec chain; the shard
  index's own codecs are not recorded. An empty index entry (offset and
  size both 2^64 - 1) is a `present=0` row. After `sharding_indexed`, a
  `crc32c` codec is allowed; any other bytes-to-bytes codec (a
  whole-shard compressor) makes the array impossible to virtualise, and
  a producer refuses it. Nested sharding is not allowed in byterefs/0.1.
  The chunk-aligned plan rule applies to the inner chunk shape.
- **JSON numbers round-trip.** A number written in a JSON column
  (`attrs`, `affine`, `codec`), or as the text of `fill`, MUST read back
  as the same IEEE 754 binary64 value that was written. 17 significant
  digits always suffice; the shortest form that round-trips is
  preferred. A single-precision attribute is written as its float32
  value converted exactly to a double. Integers are written exactly. How
  NaN and the infinities are written is not decided.
- **Chunk-aligned plan.** Each placement has step 1, `src_offset` and `dest`
  divisible by `chunks`, and `dest + count` divisible by `chunks` unless it
  reaches the end of the global axis. Otherwise the mosaic has no single
  regular chunk grid and cannot be virtualised.
- **Coordinates** come from the plan (`InlineValues` as `values`,
  `RegularlySpacedValues` as `affine`). Their CF attributes come from the
  source scan, because the mosaic VRT drops some (time `units` for OISST).
- **Publish in DELETE journal mode** (checkpoint, then `journal_mode=DELETE`),
  so a read-only remote copy opens without WAL sidecars.

## Source arrays

`placements.source_array` names what the plan reads from the source. It
takes one of these forms; anything else is an error for a reader that
rebuilds a plan (decision [0005](../decisions/0005-source-array-forms.md)).

- `<name>`: the array `/<name>` of a multidimensional source. A leading `/`
  is optional.
- `lift:<name>`: the array `/<name>`, placed with one new leading axis of
  length 1 (VRT `SourceTranspose` of `-1,0,1,...`). More leading axes and
  any permutation of the source's own axes are not allowed, as in the
  rule "Within-source keys carry the global rank".
- `band:<n>`: band `n` (1-based) of a raster source's full-resolution
  image. When the array has more dimensions than 2, the plan adds the
  leading axes, as for `lift:`.
- `band:<n>/dir:<k>`: band `n` of TIFF directory `k` (1-based, GDAL's
  `GTIFF_DIR:<k>:` numbering, where 1 is the full-resolution image). Used
  for overview levels. The source stays the file.

The prefixes `band:`, `lift:` and the suffix `/dir:` are reserved; a
multidimensional array whose own name starts with `band:` or `lift:` is
written with its leading `/`. Readers that never open the source
(kerchunk, Icechunk, Parquet readers) do not need `source_array`: the
chunk rows already carry offsets.

## Overview levels

An overview level is an ordinary array of the store, with `kind` = `data`,
whose `attrs` say which array it reduces (decision
[0006](../decisions/0006-overview-levels.md)). No table or view changes.

- `overview_of` (string, required): the array it is a reduced-resolution
  view of, in the same store.
- `overview_factor` (two or more numbers, required): the size ratio of
  `overview_of` to this array along each dimension the reduction applies
  to, in dimension order (`[y, x]` for a `[time, y, x]` array). Exact
  ratios, not rounded, not assumed to be powers of 2.
- `overview_resampling` (string, required): how the level was made
  (`AVERAGE`, `NEAREST`, `CUBIC`, ...), or `unknown`. GDAL does not record
  the method in a COG, so the producer states it from its own build.

Rules:

- A level has its own dimensions and its own coordinates, covering the
  same extent as `overview_of`. Dimensions it does not reduce (time) are
  shared.
- A level has its own `dtype`, `fill`, `codec` and CF attributes. They are
  usually those of `overview_of`, but readers must not assume it.
- A level's sources may be the same files as `overview_of` (an in-file
  pyramid, `band:<n>/dir:<k>`) or other files. Nothing in the table
  depends on which.
- The name `<array>_x<f>`, with `f` the rounded factor, is recommended,
  not required; readers find levels through `overview_of`, not by name.
- Catalog renders list `overview_of` arrays only, unless a level is asked
  for by name. Zarr renders may lay levels out as sibling arrays or as a
  multiscales group; either is a projection of the same rows.

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

looked up by the chunk table's primary key. Design m15 measured this
under 1 ms at about 1M chunks, against 0.9 to 1.9 s through the view.

The reference implementation has it: raad.virtualize's `mr_chunk_sql()`,
`mr_chunk()` and `mr_chunks()`, a batched form for the many keys a planner
asks for (mdsumner/raad.virtualize#98, closing
[#8](https://github.com/byterefs/spec/issues/8)). zaro's reader uses the
batched form (hypertidy/zaro#19).

Informative example, for an array `sst` with two dimensions, chunk shape
`(:c0, :c1)` and global chunk key `(:k0, :k1)`. It returns the verbatim
`path`; a remapped path applies the target's rules to it as in "Remap at
publish".

```sql
WITH p AS (
  SELECT source_id,
         json_extract(src_offset, '$[0]') AS so0,
         json_extract(src_offset, '$[1]') AS so1,
         json_extract(count, '$[0]') AS n0,
         json_extract(count, '$[1]') AS n1,
         json_extract(dest, '$[0]') AS d0,
         json_extract(dest, '$[1]') AS d1
  FROM placements
  WHERE array = 'sst'
)
SELECT c.present, s.source AS path, c.offset, c.size, c.info, c.data
FROM p
JOIN sst AS c
  ON c.source_id = p.source_id
 AND c.dim_0 = :k0 - p.d0 / :c0 + p.so0 / :c0
 AND c.dim_1 = :k1 - p.d1 / :c1 + p.so1 / :c1
JOIN sources AS s ON s.source_id = p.source_id
WHERE :k0 * :c0 >= p.d0 AND :k0 * :c0 < p.d0 + p.n0
  AND :k1 * :c1 >= p.d1 AND :k1 * :c1 < p.d1 + p.n1;
```

Integer division is exact here because the chunk-aligned plan rule makes
`src_offset` and `dest` multiples of the chunk shape.

## Codec mapping

| `info` | Zarr v2 | Zarr v3 |
|---|---|---|
| `COMPRESSION=DEFLATE` | compressor `zlib` | `numcodecs.zlib` |
| `COMPRESSION=ZSTD` | compressor `zstd` | `zstd` |
| `FILTER=SHUFFLE` | filter `shuffle`, `elementsize` = item size | `numcodecs.shuffle` |
| `PREDICTOR=2` (TIFF) | filter `imagecodecs_delta`, `axis` -1, `dist` 1 | `HorizontalDeltaCodec`, ahead of `bytes` |
| `ENDIANNESS=LITTLE` or `BIG` | must agree with `dtype` | `bytes` endian |

Anything else (`PREDICTOR=3`, other filters) is not mapped and stops ingest.
The Zarr v3 column is the mapping into `arrays.codec`. The Zarr v2 column
is informative, for writers of the V2 form accepted during 0.x.

## Writers and readers

| Form | Route | State |
|---|---|---|
| GDAL vector (OGR) | open the SQLite file; `refs_<array>` is a layer | works with stock GDAL |
| kerchunk Parquet (D) | `mr_write_kerchunk_parquet()` -> `blocklist::write_kerchunk_parquet()` | works; read by GDAL as `ZARR:"/vsikerchunk_parquet_ref/{dir}"` |
| zaro | `zaro("byterefs://store.sqlite")` (alias `mdimrefs://`; `target =` overrides) | works; serves Zarr v2 keys from the view; applies `meta.default_target` (hypertidy/zaro#15) |
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
   it scans the array's rows. For point lookups the placement-first join
   in "The view" avoids this, once implementations use it; materialising `refs_<array>` as a
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
| 4 | `placements.source_array` forms (`<name>`, `lift:`, `band:`, `band:/dir:`), in a new "Source arrays" section | [0005](../decisions/0005-source-array-forms.md) |
| 5 | Overview levels as arrays with `overview_of`, `overview_factor` and `overview_resampling` attributes, in a new "Overview levels" section | [0006](../decisions/0006-overview-levels.md) |
| 6 | `arrays.codec` is a Zarr V3 codec chain in encode order; the V2 form is accepted during 0.x | [0007](../decisions/0007-codec-description.md) |
| 7 | A fourth presence state: whole object, `size` NULL with `offset` 0; no placeholder sizes | [0008](../decisions/0008-unknown-chunk-size.md) |
| 8 | Sharded Zarr V3 sources are chunked at their inner chunks | [0009](../decisions/0009-sharded-zarr-sources.md) |
| 9 | Numbers in JSON columns round-trip doubles exactly | [0010](../decisions/0010-json-numbers-round-trip.md) |

No other rule, table or column has changed. Relative paths are still open (0004). In particular, this text still
describes SQLite as the store; making the Parquet export the normative
published encoding (decision 0001, brief question 7) is a later change with
its own record.
