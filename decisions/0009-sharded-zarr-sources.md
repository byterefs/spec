# 0009: Sharded Zarr V3 arrays as sources

- Status: proposed
- Date: 2026-11-08 (proposed)
- Accepted: (date and link to the acceptance pull request, when accepted)
- Closes: issue [#10](https://github.com/byterefs/spec/issues/10); part of brief question 13
- Target version: byterefs/0.1

## Context

A Zarr V3 array with the `sharding_indexed` codec stores many inner
chunks in one object (the shard). A shard index, at the start or end of
the object, gives the offset and size of each inner chunk. Every inner
chunk is a byte range of one stored object, which is exactly a byterefs
row.

zaro plans sharded arrays this way (`zaro_plan()`). It reads them
identically to zarr-python 3.2.1 and GDAL 3.14, on EOPF Sentinel-2 L2A
and on the GDAL autotest `gdrivers/data/zarr/v3` sharding fixtures.

Two cases need a rule. A `crc32c` codec after `sharding_indexed` adds 4
bytes to the end of the whole shard and leaves inner offsets unchanged.
A compressor after `sharding_indexed` compresses the whole shard, so
inner chunks have no byte range in the stored object.

This record depends on [0007](0007-codec-description.md), which describes
codecs as a Zarr V3 chain.

## Options

1. **Rows at the inner chunks.** One row per inner chunk; the shard is
   the `path`. This needs no new columns, and readers need not know about
   sharding.
2. **Rows at the shards**, with the shard index read at run time. Readers
   would have to implement sharding, and a row would no longer be one
   decodable chunk.
3. **Leave sharded sources out of 0.1.** This would exclude GeoZarr
   products that are already in use.

## Decision (proposed: option 1)

- A sharded Zarr V3 source is chunked at its inner chunks. Each inner
  chunk is one row:
  - `path` is the shard object;
  - `offset` and `size` are the inner chunk's entry in the shard index;
  - the chunk key is the inner chunk's position in the source's grid of
    inner chunks (shard key times inner chunks per shard, plus the inner
    chunk's position within the shard, on each axis).
- `arrays.chunks` is the inner chunk shape. `arrays.codec` is the inner
  codec chain from the `sharding_indexed` configuration. The shard index's
  own codecs are needed only to harvest, and are not recorded.
- An inner chunk whose index entry is empty (offset and size both
  2^64 - 1) is absent: a row with `present = 0`.
- Bytes-to-bytes codecs after `sharding_indexed` (on the whole shard):
  - `crc32c` is allowed. It does not move inner chunks, and readers of
    the table do not check it.
  - Any other (for example a compressor) means the array cannot be
    virtualized. A producer refuses it.
- Nested sharding (a `sharding_indexed` codec inside the inner chain) is
  not allowed in byterefs/0.1. A producer refuses it.
- The chunk-aligned plan rule applies to the inner chunk shape.
- Other storage that is not chunked (HDF5 contiguous datasets, TIFF
  strips, GRIB messages, files inside zip or gzip wrappers) stays open
  under brief question 13.

## Consequences

- Specification: under "Rules", a paragraph on sharded sources, with the
  `crc32c` and refusal cases. The change goes in "Changes from
  mdim-refs/0.2" with this record.
- Readers: no change. A reader sees ordinary rows.
- Producers: zaro's planner already does this. raad.virtualize does not
  read Zarr V3 sources today.
- Fixtures: a small sharded array (one with `crc32c` after sharding, and
  one with an empty inner chunk) and its expected table. A fixture with a
  whole-shard compressor that a producer must refuse. The GDAL autotest
  sharding files are a possible source.
