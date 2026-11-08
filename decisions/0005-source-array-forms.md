# 0005: Forms of `placements.source_array`

- Status: accepted
- Date: 2026-11-03 (proposed)
- Accepted: 2026-11-08, on merge of [pull request 17](https://github.com/byterefs/spec/pull/17)
- Closes: none in the brief; a gap found while indexing COG overviews
- Target version: byterefs/0.1

## Context

`placements.source_array` is specified as the "name of the array inside the
source". That covers netCDF and HDF5 sources, which GDAL opens as
multidimensional datasets with named arrays. It does not cover what the one
working producer (raad.virtualize) already writes:

| Written today | Source | Meaning |
|---|---|---|
| `temp` | netCDF/HDF5 (BRAN, OISST) | array `/temp` of the source |
| `band:1` | GeoTIFF/COG placed by a `<SourceBand>` plan (GHRSST, ESA CCI, Bedmap3, IBCSO) | band 1 of the file's full-resolution image |
| `lift:z` | 2D netCDF array stacked on a new leading axis (ASI sea ice, `SourceTranspose -1,0,1`) | array `/z`, given a length-1 leading axis by the plan |
| `band:1/dir:3` | an overview level of a COG (raad.virtualize #74, #75) | band 1 of TIFF directory 3 (GDAL `GTIFF_DIR:3:<file>`) |

A reader that rebuilds a GDAL VRT from the store (raad.virtualize's mdim VRT
render, arrir-layout) has to turn these back into `<SourceArray>`,
`<SourceBand>`, `<SourceTranspose>` and the `GTIFF_DIR:<k>:` prefix. Today
that knowledge lives only in the producer's code. Readers that never open
the source (kerchunk, Icechunk, Parquet readers) do not need it: the chunk
rows already carry offsets.

## Options

1. **Leave it to producers.** `source_array` stays a free string. Every
   reader that rebuilds a plan copies one producer's conventions; a second
   producer (VirtualiZarr, arrir) may write something else.
2. **Specify a small grammar** for the forms that exist, matching what GDAL
   can open, and reserve the prefixes.
3. **Split into columns** (`source_kind`, `source_name`, `band`,
   `directory`, `transpose`). Explicit, but a schema change for a
   conformance-only gain, and more columns than any one row uses.
4. **Put the directory in the source** (`sources.source =
   GTIFF_DIR:3:/path/file.tif`). Rejected by the producer already: every
   level of a file would become a separate source, so a rewritten file would
   not invalidate its levels together, and `sources.size`/`mtime` would be
   measured against a string that is not a file.

## Decision (option 2)

`source_array` takes one of these forms; anything else is an error for a
reader that rebuilds a plan.

- `<name>`: the array `/<name>` of a multidimensional source. A leading `/`
  is optional.
- `lift:<name>`: the array `/<name>`, placed with one new leading axis of
  length 1 (VRT `SourceTranspose` of `-1,0,1,...`). More leading axes and
  any permutation of the source's own axes are not allowed (as the
  existing "within-source keys carry the global rank" rule).
- `band:<n>`: band `n` (1-based) of a raster source's full-resolution
  image. When the array has more dimensions than 2, the plan adds the
  leading axes, as for `lift:`.
- `band:<n>/dir:<k>`: band `n` of TIFF directory `k` (1-based, GDAL's
  `GTIFF_DIR:<k>:` numbering, where 1 is the full-resolution image). Used
  for overview levels (decision 0006). The source stays the file.

The prefixes `band:`, `lift:` and the suffix `/dir:` are reserved; a
multidimensional array whose own name starts with `band:` or `lift:` is
written with its leading `/`.

## Consequences

- Spec text: the `placements` row in "Tables" points to a new "Source
  arrays" subsection holding the grammar above.
- Conformance: a check that every `source_array` parses, and that `dir:`
  appears only with `band:`.
- raad.virtualize: no change; it writes exactly these forms. Its VRT render
  already reads them.
- arrir-layout (Charles Turner): needs the `dir:` form to rebuild overview
  plans; worth agreeing the grammar together before acceptance.
- Open, not decided here: other raster formats with subdatasets or
  overview files (`.ovr`, netCDF groups) may want a `dir:`-like form;
  left until a producer writes one.
