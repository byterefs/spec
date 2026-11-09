# 0011: `arrays.dtype` is a Zarr V3 data type

- Status: proposed
- Date: 2026-11-09 (proposed)
- Accepted: (date and link to the acceptance pull request, when accepted)
- Closes: (none; follows from [0007](0007-codec-description.md))
- Target version: byterefs/0.1

## Context

`arrays.dtype` is a numpy type string (`<i2`, `<f4`), and since
[0007](0007-codec-description.md) `arrays.codec` is a Zarr V3 codec
chain. The two come from different metadata models, and a reader pointed
out that they do not mix cleanly.

1. **Byte order is said twice.** Numpy puts byte order in the type
   (`<` or `>`). Zarr V3 does not: its data types (`int16`, `float32`) have
   no byte order, and the `bytes` codec carries it as `endian`. The table
   therefore needs the rule "the `bytes` codec's `endian` agrees with the
   byte order of `dtype`", which only exists because the same fact is in
   two places.
2. **Codecs name types in V3 terms.** Some array-to-array codecs carry a
   data type in their configuration. `cast_value` (zarr-extensions) has
   `configuration.data_type`, which is Zarr V3 data type metadata
   (`"uint8"`), and its `scalar_map` writes values in the Zarr V3 fill
   value encoding of the types on either side. `scale_offset` writes
   `offset` and `scale` in the fill value encoding of its input type. A
   chain like this can only be checked against an array type in the same
   vocabulary. With a numpy `dtype`, a reader has to translate
   `<f8` to `float64` before it can tell whether the chain is valid.
3. **The endian rule is wrong once the type changes in the chain.** With
   `cast_value` ahead of `bytes`, the `bytes` codec encodes the cast type
   (say `uint8`), not the array's type (say `float64`). "`endian` agrees
   with `dtype`" then compares the wrong type: a `float64` array stored as
   `uint8` needs no `endian` at all, and one stored as `int16` needs the
   `int16` byte order, which `<f8` does not state.
4. **`fill` has no stated encoding.** `fill` is text, and decision
   [0010](0010-json-numbers-round-trip.md) leaves NaN and the infinities
   open. Zarr V3 already defines a fill value encoding per data type
   (numbers, `"NaN"`, `"Infinity"`, `"-Infinity"`, and hex strings such
   as `"0x7fc00000"` for exact bit patterns), and `cast_value` relies on
   it to cast the fill value.

In Zarr V3 array metadata the pair is `data_type` plus `codecs`; in Zarr
V2 it is numpy `dtype` plus `{compressor, filters}`. The table mixes one
half of each.

Every byterefs reader today either serves Zarr V2 keys (zaro, kerchunk
Parquet) or decodes through a V3-style chain internally (wxy-refs, zaro).
A numpy type string is easy to derive from a V3 data type and the
`bytes` codec's `endian` whenever the chain has no type-changing codec,
and the reverse is equally easy, so neither form loses information for
the arrays byterefs holds today.

## Options

1. **Keep numpy `dtype`, restrict the chain.** Disallow array-to-array
   codecs that change the type (`cast_value`) or that write values in
   V3 encodings (`scale_offset`). Small change, but it keeps byte order
   in two places and blocks a class of V3 sources without saying why.
2. **Zarr V3 data type in `dtype`, V2 form accepted during 0.x.**
   `dtype` holds a Zarr V3 data type name (`int16`, `float32`, `uint8`,
   `bool`). Byte order lives only in the `bytes` codec. `fill` uses the
   Zarr V3 fill value encoding for that type. The numpy form stays
   readable during 0.x, as the V2 codec form does under 0007. The table
   then matches Zarr V3 array metadata (`data_type`, `fill_value`,
   `codecs`).
3. **Both columns** (`dtype` numpy and `data_type` V3). Two descriptions
   of one thing, which can disagree. Rejected for the same reason as
   0007 option 4.
4. **Revert to the V2 pair** (numpy `dtype` with the V2 codec form).
   Consistent, but undoes 0007 and cannot describe V3 sources.

## Decision (option 2)

- `arrays.dtype` holds the Zarr V3 `data_type` of the array: the type of
  the decoded chunk values, which is the input to the first codec of
  `arrays.codec` in encode order. Names are those of Zarr V3 core data
  types and registered extensions (`bool`, `int8` to `int64`, `uint8` to
  `uint64`, `float16`, `float32`, `float64`, `complex64`, `complex128`,
  `r<N>`). A reader that does not know the name refuses the array.
- `dtype` carries no byte order. Byte order is the `endian` of the
  `bytes` codec in `arrays.codec`.
- **Endian rule, restated.** `endian` is required when the type that
  reaches the `bytes` codec is wider than one byte, and may be left out
  otherwise. That type is `dtype` unless an array-to-array codec ahead of
  `bytes` changes it (for example `cast_value`), in which case it is the
  type that codec outputs.
- **Fill.** `arrays.fill` is the Zarr V3 fill value encoding for `dtype`,
  written as JSON text: a JSON number, `"NaN"`, `"Infinity"`,
  `"-Infinity"`, or a hex string giving the exact bits, for floating
  types; a JSON number for integer types; `true` or `false` for `bool`.
  Numbers follow 0010. This decides NaN and the infinities for `fill`
  only; for `attrs` they stay open.
- **Transition.** During byterefs/0.x `dtype` may instead hold a numpy
  type string with an explicit byte order character (`<`, `>` or `|`, for
  example `<i2`, `|u1`). Readers tell the forms apart by the first
  character. A numpy `dtype` pairs with either codec form; when it is
  used with a V3 chain, the existing "agrees with `dtype`" rule applies,
  and the chain may not hold a type-changing array-to-array codec. Writers
  SHOULD write the V3 name. Readers MUST accept both. A `fill` written
  before this record (plain text such as `-32768` or `nan`) is read as
  before during 0.x.
- **CF packing is not moved.** CF `scale_factor` and `add_offset` stay
  verbatim in `attrs` (brief question 10), and `dtype` is then the
  packed, stored type, as today. A chain that holds `scale_offset` or
  `cast_value` describes a source that is itself Zarr V3 with those
  codecs; a producer does not turn CF attributes into codecs. Note that
  `scale_offset` and CF use opposite conventions (`scale_offset` decodes
  as `in / scale + offset`, CF as `packed * scale_factor + add_offset`),
  so a producer that ever does convert must invert the scale. Whether
  CF packing should be expressed as codecs is not decided here.

## Consequences

- Specification: in "Tables", `arrays.dtype` becomes "Zarr V3 data type
  (e.g. `int16`)" and `fill` "Zarr V3 fill value, JSON text". The codec
  chain rule's endian sentence is replaced by the restated rule above. In
  "Codec mapping", the `ENDIANNESS` row's V3 column says it sets the
  `bytes` endian (no agreement with `dtype` needed), and its V2 column
  keeps "must agree with `dtype`" for the transition form. A row in
  "Changes from mdim-refs/0.2" with this record.
- Implementations: raad.virtualize writes numpy strings today and would
  write the V3 name and move byte order to the `bytes` codec. zaro serves
  Zarr V2 keys and needs a numpy string: it derives one from the V3 name
  and the `bytes` endian (`int16` + `little` -> `<i2`), and refuses an
  array whose chain changes the type, which a V2 `.zarray` cannot state
  without a filter it may not support. wxy-refs and other V3 readers can
  use `dtype` directly. kerchunk Parquet export derives the numpy string
  in the same way. None of this is required while this record is
  proposed.
- Fixtures: one array described with a numpy `dtype` and the same array
  with a V3 name plus `bytes` endian, both reading identically; a
  `float32` array with fill `"NaN"`; and an array with an unknown data
  type name, which must be refused.
- Compatibility: existing `byterefs/0.1` and `mdim-refs/0.2` stores stay
  valid during 0.x. Whether the numpy form is still accepted at 1.0 is
  the same later record that decides the V2 codec form (0007).
