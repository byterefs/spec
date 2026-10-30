# byterefs

A byterefs table records, for every chunk of an array, which file holds it,
at what byte range, and what a reader needs to decode it. It is a plain
table: one row per chunk, readable by any SQL or dataframe engine, in any
language.

> A virtual store is not a format. It is a table of byte ranges plus a
> plan, and every format is a projection of that table.

kerchunk references, VirtualiZarr manifests, Icechunk repositories, DMR++ files and COG tile indexes all reduce to
knowing where each chunk's bytes are. byterefs is the common form those can
be generated from.

GDAL multidimensional VRTs can be used like *xarray* to logically concatenate series of files into a virtual n-dimensional array that is convenient to harvest bytes from. (Other Python approaches also provide such harvesting but they harvest for bespoke downstream usage which can be inconvenient if you aren't wedded to their tooling). Icechunk byte refs are nearly entirely opaque, but can be used as harvesters - we're not saying don't do that, just consider the flat central form championed here. 


## Status

Gate G0 (seeded). There is no normative specification yet. Start with
[BRIEF.md](BRIEF.md), which says what the specification is for, what it
covers, what is still open, and what each version must meet.

## Layout

| Path | Contents |
|---|---|
| `BRIEF.md` | purpose, scope, open questions and gates |
| `spec/` | the specification, one file per version |
| `schema/` | Arrow and Parquet schema for each version |
| `fixtures/` | source files, expected tables, oracle reads |
| `conformance/` | the check, runnable in CI |
| `decisions/` | numbered decision records, 0001 onwards |
| `prior-art/` | the survey of existing forms, with sources |
| `IMPLEMENTATIONS.md` | who produces and reads byterefs, and at which version |

## Process

A change starts as an issue, becomes a decision record in a pull request,
and lands in the specification when the record is accepted. Versions are
0.x until v1.0; each version is tagged together with its fixtures and
schema.

## Licences

- Specification text and documentation: CC-BY-4.0
  ([LICENSE-CC-BY-4.0.txt](LICENSE-CC-BY-4.0.txt)).
- Schema, fixture scripts and the conformance check: Apache-2.0
  ([LICENSE-APACHE-2.0.txt](LICENSE-APACHE-2.0.txt)).

See [LICENSE.md](LICENSE.md) for which applies where.
