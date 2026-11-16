# 0012: Chunks that are not known yet

- Status: proposed
- Date: 2026-11-11 (proposed)
- Accepted: (date and link to the acceptance pull request, when accepted)
- Closes: brief question 3 (missing chunks: known empty versus not scanned)
- Target version: byterefs/0.1

## Context

A Zarr store cannot tell a chunk that is all fill from a chunk that has
not been written yet: both are a missing key, and a reader returns fill
for both. Projects that populate arrays incrementally (Epoch, Sylvera)
work around this with a second array that records status, either an
int8 array beside the data array, or a "meta-array" group with one
element per chunk of the data array holding whatever per-chunk metadata
is needed (community advice relayed by Michael, 2026-11-11).

byterefs meets the same question in three places:

1. **Within a placed source.** The plan places a source, but some or all
   of its chunk rows have not been scanned yet (a plan written up front,
   scanning done incrementally).
2. **Outside every placement.** Part of the global array is covered by no
   placement: a hole in a COG mosaic (known nodata), or days not yet
   delivered at the end of a time axis declared in advance (not known).
3. **On render.** kerchunk, Zarr and Icechunk have the same blind spot as
   Zarr: a missing key is fill. A render that drops unknown chunks turns
   "not known" into "fill" without saying so.

Today the brief records the m17 position: a `present = 0` row is known
empty, and a missing row is unscanned and invalid to publish. That makes
an incrementally populated table unpublishable, and it says nothing about
case 2, where a VRT mosaic treats holes as nodata.

A byterefs table already is the second community option: one row per
chunk, keyed on the chunk, able to carry any column. What is missing is
a rule for what a reader does when there is no row.

## Options

For cases 1 and 2 together:

1. **Keep m17.** No row is invalid to publish; holes outside placements
   stay fill, as in a VRT. Incremental tables cannot be published, and a
   time axis declared ahead of its data reads as fill.
2. **No row means unknown; fill only from an explicit statement.** A
   `present = 0` row states fill within a source. A new fill placement
   (a `placements` row with `source_id` NULL) states fill for a slab no
   source covers. Every other key with no row is unknown.
3. **A per-array switch.** `arrays` gains a column saying whether keys
   with no row are `fill` or `unknown`. Simple, but one array cannot have
   both known holes and data not yet arrived.
4. **A status column with codes** (an int8, as in the community advice:
   pending, failed, fill, bytes, ...). Expressive, but a pending row needs
   a source to be keyed on, so it cannot cover case 2, and the codes
   beyond "unknown" are producer business.

For case 3, a writer of a form that cannot say "unknown" could refuse,
cut the render to a region with no unknown keys, or render the unknown
keys as missing and publish a status array beside it.

## Decision (option 2)

- **Three outcomes.** Every chunk key inside `arrays.shape` resolves to
  exactly one of: bytes (a `present = 1` row, in any of its forms), fill
  (a `present = 0` row, or a fill placement covering the key), or
  unknown (anything else).
- **Fill is stated, never inferred.** A fill placement is a `placements`
  row with `source_id` NULL, `source_array` NULL, `src_offset` NULL, and
  `count` and `dest` set; the chunk-aligned plan rule applies to it. Fill
  placements must not overlap placements of sources.
- **Unknown is publishable.** A published table may hold unknown keys:
  no row for a key of a placed source, or no placement covering a key.
- **Readers.** A reader MUST NOT return fill for an unknown key. It
  either refuses the read, naming the keys, or returns them as missing
  in a way the caller can tell from fill (a mask, an error value, a
  separate status result). Which is the reader's choice.
- **Writers of other forms.** A writer of a form that has no unknown
  state (kerchunk, Zarr, Icechunk) does not render unknown keys as fill
  without saying so. It refuses, renders a region that has none, or
  renders them as missing keys and writes a status array beside the
  data (informative layout below).
- **The view.** `refs_<array>` is unchanged: it holds rows of sources
  only. Fill placements are read from `placements` directly.

Informative status array for renders: an int8 array named
`<array>_chunk_status`, shape equal to the chunk grid of `<array>`
(`ceil(shape_i / chunks_i)`), with 0 unknown, 1 fill, 2 bytes, fill
value 0, attribute `chunk_status_of` naming `<array>`. This is the
community "meta-array" layout, one element per chunk; it is a
projection of the table, not a second source of truth.

## Consequences

- Specification: "Presence" gains the three outcomes and the
  fill-is-stated rule; `placements` documents fill placements; the
  "Writers and readers" section gains the render rule and the status
  array layout. A line in "Changes from mdim-refs/0.2" cites this record.
  Brief question 3 is closed.
- Compatibility: an existing store whose placements cover the whole
  global array, with every chunk row scanned, reads the same. A store
  with holes in its plan that relied on VRT nodata semantics must add
  fill placements; a producer converting from a VRT computes them as the
  uncovered slabs.
- Not decided here: held or materialized copies of chunk bytes (a Lance
  blob column, a Zarr copy). Where bytes come from is a separate
  question from whether they are known; a later record can add a held
  form of a `present = 1` row without touching these outcomes.
- Fixtures: a store with an unscanned source and a store with a time
  axis longer than its placements, both read as unknown at those keys;
  a store with a fill placement read as fill; a fill placement that
  overlaps a source placement, which must be refused.
