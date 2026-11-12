# Earthmover icechunk-datacube-ingestion skill (read 2026-11-12)

Source: https://github.com/earth-mover/agent-skills/tree/main/icechunk-datacube-ingestion
and the GOES-16 ingest it draws on (https://www.earthmover.io/blog/virtual-zarr/,
notebooks https://gist.github.com/TomNicholas/6e908090583c3c4bbed1a305ac8c3bfd and
https://gist.github.com/TomNicholas/4c441c1e69ada4d2c1e0abe35262e007).

What it is: an agent skill that walks through turning many netCDF4, HDF5,
TIFF, GRIB, Zarr or kerchunk files into one Icechunk (or Arraylake)
repository: collect requirements, confirm access, scan and write a per-file
schema, plan the concatenation, validate every file, ingest a subset then
scale with Dask, and check values against the source files.

Practices from the GOES-16 run (about 300,000 files, 7.1 billion refs,
about 80 GB of manifests):

- one commit per batch of days, appending along time;
- manifest splitting set in the repository config: split the append axis
  about as often as you commit (an unsplit manifest is rewritten on every
  commit), split space for point time series, and stay under about 100,000
  manifests per array (lookup is linear in them);
- only low-dimensional variables loaded, the data arrays left virtual;
- a write-time cache (two snapshots, bounded chunk refs) not saved to the
  repository, and dataset/session released after each commit;
- one codec per array: a codec change mid-archive becomes a separate group.

Relation to this specification: the skill's per-file references live inside
Icechunk manifests and are written straight from the files. Here the same
references are a table first (arrays.json plus refs Parquet), and Icechunk
is one projection rendered from it. The per-file schema check corresponds to
the one-codec, one-shape rules a byterefs producer enforces; the
concatenation plan corresponds to the plan (a multidimensional VRT in the
reference implementation); the source comparison corresponds to verify.

Divergence: the skill tells agents kerchunk is deprecated (September 2026)
and to discourage writing it. This specification does not follow that:
kerchunk JSON and Parquet stay supported projections, because GDAL and other
readers outside Python read them today.
