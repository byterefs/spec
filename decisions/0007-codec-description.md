# 0007: Codec description is a Zarr V3 codec chain

- Status: accepted
- Date: 2026-11-08 (proposed)
- Accepted: 2026-11-08, on merge of [pull request 17](https://github.com/byterefs/spec/pull/17)
- Closes: brief question 1; issue [#9](https://github.com/byterefs/spec/issues/9)
- Target version: byterefs/0.1

## Context

`arrays.codec` holds Zarr V2 codec ids (`{compressor, filters}`), and each
chunk row carries the block-info text in `info`. Readers already turn the
V2 form into a V3-style chain before they decode: wxy-refs maps V2 to V3 on
read, and zaro normalizes every V2 codec list to a V3 chain internally.

Some codecs have no V2 id: `crc32c`, the V3 `blosc` configuration (`cname`,
`shuffle` by name, `typesize`), byte order as the `bytes` codec, and
`sharding_indexed`. They appear as soon as a source is itself Zarr V3. EOPF
Sentinel-2 GeoZarr is one example: its inner chunks are `bytes` + `blosc`,
and its shard index is `bytes` + `crc32c`. A V2 description cannot hold
these, so such a source cannot be described today.

Decision [0001](0001-scope.md) already puts "codec chain in encode order"
in scope.

## Options

1. **Block-info text only** (`COMPRESSION=DEFLATE; FILTER=SHUFFLE`). This
   is what GDAL emits per chunk, but its vocabulary is GDAL's, it has no
   parameters (shuffle element size, compression level, blosc settings),
   and a reader still needs a mapping to decode.
2. **Zarr V2 ids** (today). Readers understand them, but V3-only codecs
   cannot be written, and every reader converts to a chain anyway.
3. **A Zarr V3 codec chain in encode order**, with the V2 form still
   accepted during 0.x. This is the form readers decode with already, and
   it covers V3 sources.
4. **Both columns** (a V2 object and a V3 chain). This means two
   descriptions of one thing, which can disagree.

## Decision (option 3)

- `arrays.codec` is a JSON array of codec objects
  `{"name": ..., "configuration": {...}}`, in encode order, as in the
  `codecs` member of Zarr V3 array metadata. It describes how the stored
  bytes of every present, referenced chunk decode to the chunk's array
  values.
- The chain holds any array-to-array codecs first, then exactly one
  array-to-bytes codec, then any bytes-to-bytes codecs. `sharding_indexed`
  is not allowed in `arrays.codec`: a chunk row references one chunk, not
  a shard. How sharded sources are described is a separate record (issue
  [#10](https://github.com/byterefs/spec/issues/10), brief question 13).
- The `bytes` codec's `endian` must agree with the byte order of `dtype`.
  For a one-byte `dtype`, `endian` may be left out.
- Codec names are those of Zarr V3 and its registered extensions (for
  example `bytes`, `gzip`, `blosc`, `zstd`, `crc32c`, and `numcodecs.*`
  names). A reader that does not know a name in the chain refuses the
  array rather than misreading it.
- **Transition.** During byterefs/0.x, `arrays.codec` may instead hold the
  V2 form `{compressor, filters}`. A reader tells the two forms apart by
  JSON type: an array is a V3 chain, an object is the V2 form. Writers
  SHOULD write the V3 chain. Readers MUST accept both. Whether the V2 form
  is still accepted at 1.0 is a later record.
- `info` per row is unchanged. The "one codec per array" rule still
  compares `info` across rows. Whether that rule is a rule of the format
  or a limit of today's readers (brief question 2) is not decided here.

## Consequences

- Specification: the `arrays.codec` entry in "Tables" becomes the V3
  chain, with the V2 form noted as accepted during 0.x. In "Codec mapping",
  the Zarr v3 column becomes the normative mapping from `info`. The Zarr v2
  column stays as informative, for writers of the transition form. The
  change goes in "Changes from mdim-refs/0.2" with this record.
- Implementations: raad.virtualize writes the V2 form today and would
  switch to the chain. zaro and wxy-refs already decode from a chain and
  need to read it from the column directly. None of this is required while
  this record is proposed.
- Fixtures: one array described each way (V2 form and V3 chain), both
  reading identically, and one array with a codec name the reader does not
  know, which must be refused.
- Compatibility: existing `byterefs/0.1` and `mdim-refs/0.2` stores stay
  valid during 0.x.
