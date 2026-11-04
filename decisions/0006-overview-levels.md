# 0006: Overview levels

- Status: proposed
- Date: 2026-11-03 (proposed)
- Accepted: (date and link to the acceptance pull request, when accepted)
- Closes: none in the brief (new question: reduced-resolution levels)
- Target version: byterefs/0.1 (attributes only; no schema change)

## Context

Every COG carries a pyramid of overview levels. Until 2026-11-03 the stores
referenced full-resolution tiles only, so a reader that wanted a coarse view
(a globe, a thumbnail, an animation) through the refs had to fetch every
full-resolution tile, or bypass the refs and walk each file's TIFF
directories. The ESA CCI chlorophyll series showed the cost: about 7 serial
header reads a month in sondage (geotiff.js), against one ranged GET per
tile through Icechunk refs.

raad.virtualize #74 and #75 index each level as an array of its own. Two
further cases came up and shape the decision:

- Levels need not be in the same file. mdsumner/rema-ovr builds a 2 m REMA
  mosaic whose GDAL `<Overview>` levels are other products (10 m and 32 m
  tile mosaics, single 100 m, 500 m and 1 km files), with factors that are
  not powers of 2 (5, 16, 50, 250, 500) and a dtype that changes between
  levels (Int16 under a Float32 base).
- Sources with no pyramid (netCDF) can only get levels that someone builds.

## Options

1. **Levels are arrays.** Each level is an ordinary array of the store, on
   its own dimensions, with attributes naming the array it reduces. No
   schema change. Readers that ignore the attributes see more arrays.
2. **A level column in the chunk tables.** One array, keyed by
   `(level, dim_*)`. Breaks the one-grid-per-array rule (each level has its
   own shape) and every existing reader.
3. **Zarr multiscales in the store.** A group per level with a
   `multiscales` attribute. byterefs has no groups, and multiscales is a
   layout choice of Zarr renders, not of the table.

## Decision (proposed: option 1)

An overview level is an array with `kind` = `data` whose `attrs` carry:

- `overview_of` (string, required): the array it is a reduced-resolution
  view of, in the same store.
- `overview_factor` (two or more numbers, required): the size ratio of
  `overview_of` to this array along each dimension the reduction applies to,
  in dimension order (`[y, x]` for a `[time, y, x]` array). Exact ratios,
  not rounded, not assumed to be powers of 2.
- `overview_resampling` (string, required): how the level was made
  (`AVERAGE`, `NEAREST`, `CUBIC`, ...), or `unknown`. GDAL does not record
  the method in a COG, so the producer states it from its own build.

Rules:

- A level has its own dimensions (named by the producer; raad.virtualize
  uses `<dim>_x<factor>`) and its own coordinates, covering the same extent
  as `overview_of`. Dimensions it does not reduce (time) are shared.
- A level has its own `dtype`, `fill`, `codec` and CF attributes. They are
  usually those of `overview_of`, but readers must not assume it.
- A level's sources may be the same files as `overview_of` (an in-file
  pyramid, `band:<n>/dir:<k>`, decision 0005) or other files (built
  overviews, a mosaic of other products). Nothing in the table depends on
  which.
- Name: `<array>_x<f>` with `f` the rounded factor is recommended, not
  required; readers find levels through `overview_of`, not by name.
- Catalog renders (STAC variables, grist rows) list `overview_of` arrays
  only, unless a level is asked for by name.
- Zarr renders may lay levels out as sibling arrays (raad.virtualize now)
  or as a multiscales group; either is a projection of the same rows.

## Consequences

- Spec text: an "Overview levels" section with the attributes and rules
  above. No change to tables or the view.
- Conformance: `overview_of` names an array of the store; the factor has
  one entry per reduced dimension; the level's extent matches its base
  within half a cell.
- raad.virtualize already writes these attributes (#74, #75).
- Left open: held or derived levels (bytes the producer computed and keeps
  next to refs, "held" rows), and a recipe attribute for levels built on
  demand. Both wait on the held-bytes and versioning questions.
