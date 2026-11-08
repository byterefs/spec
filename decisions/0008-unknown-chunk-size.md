# 0008: Rows whose size is not known

- Status: accepted
- Date: 2026-11-08 (proposed)
- Accepted: 2026-11-08, on merge of [pull request 17](https://github.com/byterefs/spec/pull/17)
- Closes: issue [#12](https://github.com/byterefs/spec/issues/12); touches brief questions 3 and 8
- Target version: byterefs/0.1

## Context

Every referenced row carries `size`. A native Zarr chunk is a whole
object, and its size is not known without a request (a HEAD, or a
listing). A producer that virtualizes Zarr stores (zaro, planned) has to
either measure every object or leave the size unrecorded.

The same gap comes up when converting between byterefs and other
reference stores (kerchunk, VirtualiZarr manifests, Icechunk). Some of
them hold a whole-object reference (kerchunk `[url]`) or a placeholder in
place of a real length. A conversion that copies a placeholder into
`size` as if it were measured would make the table say something false.

## Options

1. **Require `size` on every published row.** Producers measure, or use a
   listing's size. This keeps the integrity checks whole, but it makes
   lossless conversion from formats with whole-object or placeholder
   references impossible without extra requests.
2. **Allow `size` NULL in a working store only**, and require it filled
   before publishing. Same cost for conversions as option 1, deferred.
3. **Allow `size` NULL in published tables, meaning the whole object.**
   This keeps conversions lossless and honest. It weakens a few checks for
   those rows only.

## Decision (option 3)

- A present, referenced row with `offset = 0` and `size` NULL refers to
  the whole object at `path`, with its length not recorded. A reader
  fetches the whole object.
- `size` NULL with any other `offset` is invalid. `offset` NULL keeps its
  existing meaning (an inline chunk, `data` set).
- A writer never stores a placeholder or sentinel as `size`. If a source
  format holds one in place of a real length, the converter writes NULL.
- A writer SHOULD record sizes it knows. A size from an object listing is
  good enough.
- A writer of a form that needs a length (for example Icechunk virtual
  chunk references) measures the object, or refuses the row. It never
  supplies a value of its own.

## Consequences

- Specification: the "Presence" rule gains this fourth case (present,
  whole object, length not recorded). The remap rule's statement that
  `size` holds across targets applies only where `size` is set.
  `sources.size` checks cannot be made against these rows. The change goes
  in "Changes from mdim-refs/0.2" with this record.
- Readers: one more row state. Range coalescing and read budgets are not
  available for these rows.
- Fixtures: a store with a whole-object row read identically to one with
  the size recorded; a row with `size` NULL and a non-zero `offset`,
  which must be refused.
- Compatibility: existing stores have every size set, so they stay valid.
