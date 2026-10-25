# byterefs: brief

Status: brief, 2026-10-25. Seeds the `byterefs` organisation on GitHub.
This is not a specification. It says what the specification is for, what
it covers, what is still open and where each open question currently
lives, and what has to be true before each version is called done.

## 1. What a byterefs table is

A byterefs table records, for every chunk of an array, which file holds
it, at what byte range, and what a reader needs to decode it. Nothing
more. It is a plain table: one row per chunk, readable by any SQL or
dataframe engine, in any language.

The stance, from which everything else follows:

> A virtual store is not a format. It is a table of byte ranges plus a
> plan, and every format is a projection of that table.

kerchunk references, a VirtualiZarr manifest, an Icechunk repository, a
GDAL multidimensional VRT, a DMR++ file and a COG's tile index all reduce
to knowing where each chunk's bytes are and pointing a reader at them.
byterefs is the common form those can be generated from.

## 2. Why it should exist

Most environmental and earth observation archives are not cloud-native,
and they will not be rewritten. They do not need to be. Every chunk of
every array already sits at a known byte range in a file someone is
already serving. What is missing is a neutral place to write those ranges
down.

Today the knowledge is held in several places, each with its own shape:

- in memory, inside the tool that scanned the files;
- in a format-specific manifest (kerchunk JSON or Parquet, Icechunk
  manifests, DMR++);
- inside a file format's own index (TIFF tile offsets, the HDF5 chunk
  B-tree), which has to be read file by file.

That has four costs.

1. **Harvesting is repeated.** Each tool scans the same files again to
   build its own form. Reading chunk indexes out of thousands of HDF5
   files is the expensive step, and it is done once per tool rather than
   once per file.
2. **References are trapped.** A reference written as one format is
   awkward to turn into another, so a choice of reader becomes a choice
   of store.
3. **Defects hide.** Byte-identity tests compare offsets and sizes, which
   are integers and easy to check. The defects that matter in practice
   are in the description: a packing attribute rounded on the way
   through, a fill value that disagrees between the format layer and the
   CF attributes. Two builds of the same dataset can differ in meaning
   while agreeing on every byte range (design m17 in wxylib/design records
   both cases in a real store).
4. **Addressing is ad hoc.** Moving references from an HPC mirror to a
   public URL is done by editing paths in whatever form was written.

A plain, durable table answers all four. It is produced once per source
file. Every published form is rendered from it. Its description can be
checked against the source independently of its bytes. And because byte
offsets do not change when a file is copied byte for byte, a table built
by scanning a fast local mirror can point at a public URL: remapping is
data, not an edit.

This argument does not depend on any particular implementation. The
specification must stand without one.

## 3. Prior art

Each existing form records the same per-chunk facts (where, how many
bytes, how to decode) in its own container. Snapshot of primary sources as
of 2026-10-25; the full survey with links is in `prior-art/survey-2026-10.md`.

| Form | Per chunk | Codecs | Missing / inline | Integrity | Grid |
|---|---|---|---|---|---|
| kerchunk JSON v0/v1 | key -> `[url, offset, length]`, or a string (inline) | Zarr v2 `.zarray` | missing: key absent; inline: string, `base64:` for binary | none | Zarr v2 regular |
| kerchunk Parquet (fsspec `LazyReferenceMapper`) | `path`, `offset`, `size`, `raw`; row = C-order chunk index, `record_size` rows per file | Zarr v2 in `.zmetadata` | missing: `path` and `raw` null; inline: `raw` | none | Zarr v2 regular |
| VirtualiZarr `ChunkManifest` | `paths`, `offsets`, `lengths` arrays shaped like the chunk grid | Zarr v3 array metadata | missing: path `""`; inline: path `"__inlined__"` | none in the manifest | regular only (rectilinear planned) |
| Icechunk manifest (spec 2.1) | `index`, `location`, `offset`, `length`; or `inline` (encoded bytes) | Zarr v3 array metadata | inline: `inline` field; missing: no ref (not confirmed in spec text) | `checksum_etag` or `checksum_last_modified`, enforced with conditional requests | Zarr v3 grid |
| DMR++ | `offset`, `nBytes`, `chunkPositionInArray` (element, not chunk, indices), filter mask | `compressionType` filter pipeline in order | missing: chunk omitted, `fillValue`; inline: `dmrpp:compact` | none | regular |
| GDAL `GetRawBlockInfo` (since 3.12) | filename, offset, size, driver key/value info, inline data | `COMPRESSION`, `FILTER`, `ENDIANNESS`; Zarr driver adds compressor JSON | missing: all fields empty; inline: data set, filename null | none | the driver's block grid |
| GDAL `gdal mdim get-refs` subcommand (draft, OSGeo/gdal PR 14677) | `dim_0..dim_{n-1}`, `present`, `path`, `offset`, `size`, `info` as an attribute-only vector layer | `info` text per row; codec layer metadata | absent: nulls; inline: planned | none | the array's block grid |
| TIFF / COG | `TileOffsets`, `TileByteCounts` per IFD | TIFF tags (compression, predictor) | sparse tiles: offset and count 0 | none | regular tiles |

Zarr itself has two related proposals: a chunk manifest storage
transformer (zarr-specs issue 287, open or closed state unverified) and the
`rectilinear` chunk grid in zarr-extensions, now implemented as
experimental in zarr-python.

What none of them is: a plain table that is the same thing in every
language, carries source integrity, keeps "known empty" apart from "not
scanned", treats remapping as data, and states the meaning of the values
(fill, packing) in a form a check can compare with the source.

## 4. Starting point: mdim-refs/0.2

byterefs does not start from nothing. A working draft, mdim-refs/0.2,
already exists in wxylib/design (`specs/mdim-refs-0.2.md`), with three
design records that test it against real stores:

- m15: the draft against its reference implementation and two live
  stores, BRAN2023 daily temperature (1,116,900 chunks, netCDF4 over
  THREDDS) and GHRSST MUR analysed_sst (22,766,292 chunks for the full
  series, COGs);
- m16: holding the table with history (Lance, Parquet fragments with a
  manifest commit, Icechunk with daily commits);
- m17: what a published store must state about meaning, as opposed to
  layout, and a one-file conformance check.

What mdim-refs/0.2 has settled, and byterefs should keep unless a
decision record says otherwise:

| Settled | Rule |
|---|---|
| Three layers | physical rows keyed within each source; a plan placing sources in a global array; a view computed from the two |
| Source rule | a source is the URI opened at scan time, verbatim; offsets are bound to it |
| Remap at publish | published paths come from prefix rules per target; never written into the source rows |
| Presence | present and referenced, present and inline, known empty |
| One codec per array | a source whose chunks disagree cannot join the array |
| 64-bit byte columns | offsets and sizes are signed 64-bit integers |
| Chunk-aligned plan | a placement starts and ends on chunk boundaries, or the array cannot be virtualised |

It has been validated on OISST (16,387 sources), BRAN2023 and MUR, with
reads through GDAL on rendered kerchunk Parquet, through zaro on the
table, and through GDAL on the source agreeing.

What mdim-refs/0.2 is not: it is named for GDAL's multidimensional model,
it lives inside one implementation's design repository, and its
published encoding (Parquet export) is explicitly not fixed. byterefs
0.1 is that draft lifted out, renamed, and made normative.

## 5. Scope

In scope:

- **Reference rows**: chunk key, source, offset, size, presence, inline
  bytes for small chunks.
- **Array description**: dimension names, shape, chunk shape, data type
  and byte order, fill value, codec chain in encode order, packing
  attributes verbatim, and the CF attributes needed to read values
  correctly.
- **Sources**: identity and integrity (size, modification time, entity
  tag, optionally a checksum).
- **Remap rules**: how a published path is derived from a source for a
  named target.
- **A published encoding**: the Parquet layout a reader can rely on. A
  producer may keep any working encoding (SQLite, Lance, in memory); only
  the published form is normative.
- **Conformance**: fixtures, expected tables, and a check.

Out of scope:

- **Chunk bytes**, beyond inline storage of small chunks.
- **Versioning and transactions.** History can be held by a table format
  that already does it (design m16 measured Lance, Parquet fragments and
  Icechunk); byterefs describes one state of the table.
- **Catalogues and discovery.** A catalogue points at a published table;
  it does not hold references.
- **Georeferencing semantics** beyond carrying the source's attributes.
  Grids, frames and coordinate reference systems belong to the formats
  and conventions that already describe them (CF, GeoZarr, GDAL).
- **Rendering.** Writers of kerchunk, Icechunk, VRT and other forms are
  implementations, not part of the specification.

The plan layer (where each source's slab sits in a global array) is the
one boundary not yet drawn; see open question 6.

## 6. Open questions, and where each lives now

| # | Question | Where it stands now |
|---|---|---|
| 1 | **Codec description.** GDAL block-info text (`COMPRESSION=DEFLATE; FILTER=SHUFFLE`), Zarr v2 codec ids, or a Zarr v3 codec chain? | mdim-refs/0.2 stores block-info text per row and a v2 codec object per array, with a mapping table; wxy-refs maps v2 to v3 on read |
| 2 | **Codec per array or per chunk.** Is "one codec per array" a rule of the format, or a limit of today's readers? | mdim-refs/0.2 rule; m15 section 3.5 |
| 3 | **Missing chunks.** Known empty versus not scanned. | m17 section 4: a `present = 0` row is known empty; no row is unscanned and invalid to publish |
| 4 | **Inline chunks.** Size threshold, encoding, and whether inline bytes are encoded or decoded. | mdim-refs/0.2 `data` column; kerchunk `raw` |
| 5 | **Chunk grid.** Regular only, or rectilinear (per-axis chunk edges)? | mdim-refs/0.2 open question 4; wxylib/design m10 (overlapping COG mosaics); the Zarr rectilinear chunk grid proposal |
| 6 | **Plan in or out.** Keep placements in the table, or point at a plan held elsewhere (an mdim VRT, a Zarr hierarchy)? | mdim-refs/0.2 open question 2; placements duplicate the VRT but let SQL-only readers compute the view |
| 7 | **Published layout.** One self-describing Parquet file per array or per store; metadata in key-value footer or a sidecar; row groups along the first dimension; dictionary-encoded paths. | mdim-refs/0.2 open question 5; m15 section 3.1; m17 `store.json` |
| 8 | **Source integrity.** Which of size, mtime, entity tag and checksum are required, and what a reader does on mismatch. | mdim-refs/0.2 `sources`; Icechunk virtual chunk fields |
| 9 | **Remap semantics.** Longest-prefix rules per target, templates, or both; relative paths. | mdim-refs/0.2 `remap`; wxy-refs resolves relative paths against the table's directory; kerchunk templates |
| 10 | **Description contract.** Which statements about meaning are required (fill agreement, packing verbatim, time units and calendar, provenance). | m17 MUST and SHOULD lists, reconciled in m17 section 4 |
| 11 | **Chunk keys.** `dim_0 .. dim_{n-1}` integer columns, zero-based, C order, against named dimension columns. | GDAL block-info draft and mdim-refs/0.2 use `dim_i` |
| 12 | **Lower-rank sources.** A 2D tile placed in a 3D stack; transposes. | mdim-refs/0.2 rule (keys carry the global rank; no permutation); m15 section 3.7 |
| 13 | **Storage that is not chunked.** HDF5 contiguous datasets, TIFF strips, GRIB messages, files inside zip or gzip wrappers. | wxylib/design m14 section 3 (format classes and harvest cost) |
| 14 | **Relation to GDAL.** Align column names with GDAL's raw block information output, or define them independently and map. | the GDAL subcommand (`gdal mdim get-refs`, PR 14677) is in review and its name may still change; its draft columns are those of mdim-refs/0.2 |
| 15 | **Name of the format identifier.** `byterefs/0.1` in metadata; whether mdim-refs/0.2 tables are accepted as a legacy identifier. | new |

Each question is closed by a numbered decision record in `decisions/`,
not by an edit to the specification alone.

## 7. Gates

A version is done when its gate is met, not when its text is written.

**G0: seeded.**

- [x] Repository created with README, this brief, licences and a
      contributing note.
- [x] Decision 0001 (scope, from section 5) and decision 0002 (start from
      mdim-refs/0.2) written (status proposed; acceptance is a separate
      pull request, see `decisions/README.md`).
- [x] Prior art in section 3 checked against primary sources. Note: the
      open or closed state of zarr-specs issue 287 and OSGeo/gdal pull
      request 14677 is still unverified; see the verification note in
      `prior-art/survey-2026-10.md`.

**v0.1: one regular array, from one or more sources.**

- [ ] Normative text for reference rows, array description, sources,
      presence and remap.
- [ ] The Parquet published layout fixed (question 7), with a schema file.
- [ ] Questions 1, 2, 3, 4, 8, 9, 11 and 15 decided.
- [ ] Fixtures, each a small source file with its expected table and an
      oracle read: netCDF4/HDF5 with deflate and shuffle; a COG with a
      predictor; an array with known-empty and inline chunks.
- [ ] Two independent implementations produce the expected tables from
      the fixtures.
- [ ] One rendering to kerchunk Parquet and one to a GDAL multidimensional
      VRT, each reading equal to GDAL on the source.
- [ ] The description check (m17's contract, as decided for v0.1) runs
      over the fixtures in CI.

**v0.2: collections.**

- [ ] Question 6 decided: the plan layer, or a reference to a plan.
- [ ] Questions 10 and 12 decided.
- [ ] Fixtures for a multi-source array, a lower-rank source and two remap
      targets.
- [ ] A content summary (present, known empty, total, bytes) defined and
      checked.

**v0.3: beyond regular chunking.**

- [ ] Question 5 decided, with a fixture from an overlapping mosaic.
- [ ] Question 13 decided for at least contiguous HDF5 and TIFF strips.
- [ ] One rendering to Icechunk virtual references reading equal to the
      source.

**v1.0: stable.**

- [ ] Review by people from at least two implementation communities
      other than the authors'.
- [ ] A compatibility and versioning policy.
- [ ] Every open question closed or explicitly deferred to a named later
      version.
- [ ] A decision on whether to offer the specification to a community
      body.

## 8. Repository layout

```
README.md            what byterefs is, in one screen
BRIEF.md             this document
spec/                byterefs-0.1.md and later versions
schema/              Arrow and Parquet schema for each version
fixtures/            source files, expected tables, oracle reads
conformance/         the check, runnable in CI
decisions/           numbered decision records, 0001 onwards
prior-art/           the survey behind section 3, with sources
IMPLEMENTATIONS.md   who produces and reads byterefs, and at which version
```

Licences: specification text CC-BY-4.0; schema, fixtures scripts and the
conformance check Apache-2.0.

Process: a change starts as an issue, becomes a decision record in a pull
request, and lands in the specification when the record is accepted.
Versions are 0.x until v1.0; each version is tagged together with its
fixtures and schema.

## 9. Implementations at the start

These are where the ideas were worked out. They are listed so the
specification can be measured against them; none of them defines it.

| Implementation | Role | State |
|---|---|---|
| wxylib/core `wxy-refs` (Rust) | reads the mdim-refs/0.2 Parquet export; serves Zarr; writes Icechunk | working, oracle-tested against wxylib/fixtures |
| raad.virtualize (R, SQLite) | producer: scans sources, holds the store, renders kerchunk, Icechunk, VRT and STAC | working on OISST, BRAN2023, MUR |
| zaro (R) | reads the table as a Zarr store | pull request |
| blocklist (R) | writes kerchunk Parquet | working |
| GDAL `GetRawBlockInfo` (3.12) and the proposed `gdal mdim` subcommand | emits per-chunk rows from HDF5, netCDF, Zarr and VRT sources | API released; subcommand under review |
| virtual-cog-pilot (browser) | harvests COG tile offsets and reads kerchunk Parquet in the page | pilot |
| cogcache, rwarp | consumers of chunk references in a warp pipeline | experimental |

## 10. First steps

1. Create the repository; commit this brief, README and licences.
2. Write decisions 0001 and 0002.
3. Move the prior-art survey into `prior-art/` with its sources.
4. Copy the mdim-refs/0.2 text into `spec/byterefs-0.1.md` as the starting
   draft, with a changes section that will record every departure.
5. Take the smallest wxylib/fixtures `mdimrefs/` cases as the first
   fixtures.
