# 0013: Holding the byte-ref table with history: Parquet fragments and a manifest, Lance later

- Status: proposed
- Date: 2026-11-13 (proposed)
- Accepted: (date and link to the acceptance pull request, when accepted)
- Closes: none (brief section 5 puts versioning and transactions out of
  scope; this records the producer practice that sits beside the format)
- Target version: byterefs/0.1 (non-normative for 0.1)

## Context

byterefs describes one state of the table (brief section 5). A producer
that publishes a store more than once (daily appends, prelim to final,
a reprocessed collection) still has to keep history somewhere, and
readers have to be able to pin "the table as it was". The question has
been open since wxylib/design m16 measured three ways of doing it (Lance,
Parquet fragments with a manifest commit, Icechunk with daily commits),
and it is gap 10 in the bytes-in-place note.

It needs deciding now because the published stores are moving towards
production on source.coop, and a producer should know which form to
write before there are many stores in one form or the other.

## Options

1. **Lance.** Versions and tags, serverless commits by
   put-if-not-exists of `_versions/{n}.manifest` (the table-side twin of
   Icechunk's commit), blob columns for held bytes, `merge_insert`
   upserts. m16 measured a held-chunk take of 1 ms against 29 ms for
   Parquet with 64-row groups. Against it, for our readers today:
   - R: the DuckDB `lance` core extension (DuckDB 1.5.5, lance 6.0) reads
     plain columns with `dim_*` pushdown, but blob columns fail or crash
     and there is no time travel (`AT (VERSION => ...)` is refused).
     Tested 1 Nov 2026, project note `lance-duckdb/README.md`. So R gets
     the latest version of the ref side only.
   - SedonaDB (Jia Yu, 3 Nov 2026): reads Lance through a Python
     `ExternalFormatSpec` over Arrow C streams, with pinned versions,
     tags and blobs as `LargeBinary`, but filters apply after the scan.
     A `__sedonadb_table_provider__` C ABI could give pushdown and an R
     import; untested with Lance, experimental.
   - Lance object stores read s3, gs, az and file, not https, so a
     source.coop store needs an s3 twin remap target.
   - Lance's DataFusion provider must match DataFusion's major version,
     which pins every engine that embeds it.
   - GDAL has no reader.
2. **Parquet fragments and a manifest.** Each publish writes new,
   immutable Parquet fragments; a small manifest (one file per version,
   written last) lists the fragments that make up that version. A reader
   pins a version by reading its manifest. Every reader we have (arrow,
   duckdb, GDAL's Parquet driver, polars, pyarrow) reads the fragments
   today, R included. Against it: no transactions beyond "write the
   manifest last", no key constraint, no held-bytes blob type, and the
   commit protocol is ours. The same pattern already runs in the listing
   corpus (aad-filelist `runs/<id>/<run_id>.parquet` plus `runs.parquet`
   and `current/`) and in raad.virtualize's harvest fragments.
3. **Iceberg** (as in Earthmover's "Icechest", Iceberg tables inside an
   Icechunk commit, CNG 2026). Mature tables and snapshots, but it needs
   a catalog, and its R path is no better than Lance's.
4. **Icechunk as the store of record.** Already a sink (bytes-in-place
   section 5). It holds history for the rendered Zarr, not for the
   table, and most of what we version is already a column (prelim and
   final are two sources; a daily append is new rows keyed by source).

Advice: Dewey Dunnington (Arrow, R; relayed by Michael, 13 Nov 2026):
"Lance is definitely the fancier solution ... Parquet will probably be
sufficient while we wait for R / Lance to catch up."

## Decision (option 2, Lance revisited later)

- A producer that keeps history of a byte-ref table SHOULD hold it as
  immutable Parquet fragments plus one manifest per version. Each
  fragment is a valid byterefs table (or a valid part of one) on its
  own; history is never encoded in the byterefs columns themselves.
- A version is published by writing its manifest after every fragment
  it lists exists. A manifest is never rewritten; a new version is a
  new manifest. Concurrent writers are not supported; one writer per
  store.
- The manifest layout (file name, columns, how "latest" is found) is
  producer practice for now and is not part of byterefs/0.1. It is
  written down by the first implementation that publishes one, and can
  become a later decision if a second producer needs to agree with it.
- Lance stays the preferred future form, for held bytes first (where
  versioning pays for itself; a ref cannot recover bytes that changed at
  the origin, an older Lance tag can). Revisit this record when any of
  these holds: R reads Lance blob columns and pinned versions (through
  the DuckDB extension, SedonaDB, or arrow); a store needs held bytes;
  a store needs more than one concurrent writer.
- Iceberg and Icechunk are not used as the store of record for the
  table. Icechunk stays a render.

## Consequences

- Specification: no normative change. Section 5's "Versioning and
  transactions" bullet can point at this record.
- Notes: gap 10 in `notes/bytes-in-place.md` (versioned byte-ref table)
  is answered for the refs side; the held-bytes side stays open until
  the Lance revisit.
- Implementations: raad.virtualize's publish step is the first place a
  manifest would be written; it already writes per-source fragments at
  harvest. No reader change is needed to read one version.
- Fixtures and conformance: none. A conformance check runs against one
  version (one manifest's fragments read as one table).
- If this record is superseded by a Lance record, a Parquet history
  converts to Lance versions one manifest at a time.
