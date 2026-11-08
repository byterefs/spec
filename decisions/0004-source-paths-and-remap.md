# 0004: Source paths and remap

- Status: accepted
- Date: 2026-11-03 (proposed)
- Accepted: on merge of [pull request 7](https://github.com/byterefs/spec/pull/7)
- Closes: brief question 9, except relative paths (left open)
- Target version: byterefs/0.1

## Context

A table is often built by scanning a fast local mirror (`/g/data/...` on
NCI, `/rdsi/PUBLIC/...` on the AAD mirror) and then read by people who can
only reach a public endpoint (NCI THREDDS, source.coop, an S3 bucket).
Byte offsets survive a byte-for-byte copy, so the same rows serve both,
provided the path can be changed.

The starting draft (mdim-refs/0.2) records the scanned URI verbatim in
`sources.source` and holds prefix rules in a `remap` table, applied only
when a form is rendered. Its rules are written for the SQLite store. The
published Parquet encoding (brief question 7) is not fixed, and nothing
says what a reader of it does with a path it cannot open.

The concern raised on pull request 3: a published flat table that carries
`/g/data/...` or `/rdsi/PUBLIC/...` paths leaks site-local layout, and a
plain Parquet reader that ignores the rules gets paths that do not
resolve. The suggestion in reply: carry the local-to-public mapping with
the table, in the Parquet footer or a sidecar.

## Options

1. **Rewrite at harvest.** Store the public URL in `sources.source`.
   Simple for readers. Loses the URI the offsets and integrity fields were
   measured against, breaks "scan the sources not already in the store"
   when the public form of a path changes, and gives one target only.
2. **Verbatim source, remap rules travel with the table.** The mdim-refs/0.2
   model, extended to the published encoding. One table serves every
   target (public https, `/vsicurl/` for GDAL, in situ for users on the
   HPC system). Readers must apply the rules.
3. **Templates** (kerchunk `templates`, `{{u}}/file.nc`). Shorter rows,
   but the path is no longer a plain string, and every reader needs a
   template engine. Prefix rules give the same saving when `path` is
   dictionary-encoded.
4. **Both columns per row** (verbatim and public). The `public` column of
   aad-filelist 0.1. Fixes one target per table and doubles the path data.

Evidence, as of 2026-11-03:

- raad.virtualize already does option 2 in its flat refs store: paths are
  written verbatim and the rules travel in `arrays.json`
  (`R/mdimrefs_pipeline.R`, `mr_write_flat`). wxy-refs applies the target
  it wants. The kerchunk, Icechunk and VRT forms are rendered with paths
  already remapped (`config/bran.sh`: targets `public` and `gdal`).
- Rendered forms therefore never expose `/g/data`; the flat store, the
  SQLite store and `sources.parquet` do.
- The 2026-10-03 validation compared 120 of 120 rows from the `/rdsi`
  mirror and the NOAA S3 copies on offset and size: a remap is only
  correct where the endpoints hold the same bytes.

## Decision

Option 2, with three additions for the published encoding.

- **Source rule unchanged.** `sources.source` is the URI opened at scan
  time, verbatim. Integrity fields (size, mtime, entity tag) are bound to
  it.
- **Rules travel with the published table.** The published encoding
  carries the remap rules as a list of `{target, prefix, replacement}`.
  A published path for target T is the source with the longest matching
  `prefix` among T's rules replaced by `replacement`; a source no rule
  matches is used verbatim. Where the rules live (Parquet key-value
  metadata or a sidecar) is decided with the published layout (brief
  question 7); this record requires only that they are part of it.
- **Default target.** The published metadata states `default_target`. A
  reader not told a target applies the default. A store meant for public
  use SHOULD name a default target under which every source resolves
  without site access. The empty string means verbatim.
- **A rule asserts byte identity.** A rule claims that the bytes at the
  replacement are the bytes that were scanned. A producer SHOULD check a
  sample of chunks through each target it publishes. Size applies across
  targets; mtime and entity tag apply to the verbatim source only.
- **No confidentiality.** The format does not hide a local root. A
  producer that must not disclose one publishes from a copy of the store
  with a target applied to `sources.source` and that target's rules
  dropped. The result is a valid store whose sources are the public URIs;
  its integrity fields still hold because of the byte-identity assertion.
- **Prefix rules only.** No templates. Relative paths (wxy-refs resolves
  them against the table's directory) are left open for a later record.

## Consequences

- `spec/byterefs-0.1.md`: the "Remap at publish" rule gains
  `default_target`, the byte-identity statement and the no-confidentiality
  note; the Parquet layout record (question 7) places the rules.
- Schema: `meta` gains optional `default_target`; the published metadata
  carries `remap`.
- raad.virtualize: `mr_write_flat` writes `default_target` (for example
  `public` in `config/bran.sh`); `verify-published` already reads each
  form back through its target.
- Readers (wxy-refs, arrir-layout, zaro): apply `default_target` when no
  target is given. zaro: done (hypertidy/zaro#15).
- The specification gives a short informative SQL example that applies
  the rules, so a plain DuckDB reader gets resolvable paths.
- Fixtures: two remap targets over one store, a source that no rule
  matches, and a store published with its local root removed.
- Conformance: a published store with `remap` rules and no
  `default_target` is a warning; one whose rules name an unknown target is
  an error.
