# 0002: Start from mdim-refs/0.2

- Status: proposed
- Date: 2026-10-25
- Target version: byterefs/0.1

## Context

A working draft, mdim-refs/0.2, exists in wxylib/design
(`specs/mdim-refs-0.2.md`), tested against live stores in design records
m15, m16 and m17 and validated on OISST (16,387 sources), BRAN2023 and MUR.
It is named for GDAL's multidimensional model, lives inside one
implementation's design repository, and does not fix its published
encoding. See [BRIEF.md](../BRIEF.md) section 4.

## Decision

byterefs 0.1 starts as the text of mdim-refs/0.2, lifted out, renamed and
made normative. The following rules are kept unless a later decision record
says otherwise:

| Rule | Statement |
|---|---|
| Three layers | physical rows keyed within each source; a plan placing sources in a global array; a view computed from the two |
| Source rule | a source is the URI opened at scan time, verbatim; offsets are bound to it |
| Remap at publish | published paths come from prefix rules per target; never written into the source rows |
| Presence | present and referenced, present and inline, known empty |
| One codec per array | a source whose chunks disagree cannot join the array |
| 64-bit byte columns | offsets and sizes are signed 64-bit integers |
| Chunk-aligned plan | a placement starts and ends on chunk boundaries, or the array cannot be virtualised |

## Consequences

- `spec/byterefs-0.1.md` begins as a copy of mdim-refs/0.2 with a "Changes
  from mdim-refs/0.2" section that records every departure and the decision
  that made it.
- Whether mdim-refs/0.2 tables are accepted under a legacy identifier is
  brief question 15, decided separately.
