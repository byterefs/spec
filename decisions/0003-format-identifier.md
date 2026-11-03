# 0003: Format identifier

- Status: accepted
- Date: 2026-11-02 (proposed)
- Accepted: on merge of [pull request 3](https://github.com/byterefs/spec/pull/3)
- Closes: brief question 15
- Target version: byterefs/0.1

## Context

Tables written from the starting draft carry `format_version` =
`mdim-refs/0.2`. That name comes from a GDAL subcommand draft (`gdal mdim
get-refs`) that is shelved, and that should return as `gdal mdim
chunk-info`. It also ties the format to GDAL's multidimensional model,
while a byterefs table describes bytes in files whatever model reads them.

Brief question 15 asks what the identifier is, and whether mdim-refs/0.2
tables are accepted under a legacy identifier.

## Options

1. Keep `mdim-refs/0.x` as the identifier and use byterefs only as the name
   of the project.
2. Use `byterefs/0.x`, and accept `mdim-refs/0.2` as a permanent legacy
   identifier.
3. Use `byterefs/0.x`, and accept `mdim-refs/0.2` only for a stated
   transition.

Evidence for the choice, as of 2026-11-02:

- Every table published with `mdim-refs/0.2` is a draft index in a scratch
  location (raad.virtualize on source.coop `ausantarctic-scratch` and the
  AADC staging prefix). They are rebuilt from their sources as a matter of
  course; a full bluelink daily variable rebuilds in about 16 minutes.
- The one external binding, ArrIR's `arrir-layout`, is in design and has
  not been released.

## Decision

Option 3.

- A byterefs table states its version in `format_version` as
  `byterefs/<major>.<minor>`, for example `byterefs/0.1`.
- A reader of byterefs/0.1 may accept `mdim-refs/0.2` as equivalent to
  `byterefs/0.1` during the transition. A producer must not write
  `mdim-refs/0.2` once byterefs/0.1 is tagged.
- The transition ends when byterefs/0.2 is tagged. After that, readers
  need not accept `mdim-refs/0.2`.
- The identifier names the format only. It does not depend on GDAL's
  naming; column names stay aligned with GDAL raw block information
  (brief question 14) independently of it.

## Consequences

- `spec/byterefs-0.1.md` requires `format_version` = `byterefs/0.1`.
- Producers (raad.virtualize) change the identifier they write, and rebuild
  their scratch tables before byterefs/0.2.
- Readers (wxy-refs, arrir-layout, zaro, raad.virtualize's Icechunk
  render) accept both identifiers until byterefs/0.2.
- The name `byterefs` itself stays open to wider discussion before v1.0;
  a rename then would be a new record superseding this one.
