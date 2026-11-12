# 0011: Named remap roots for relocatable projections

- Status: proposed
- Date: 2026-11-12 (proposed)
- Accepted: (date and link to the acceptance pull request, when accepted)
- Closes: none (extends [0004](0004-source-paths-and-remap.md))
- Target version: byterefs/0.1

## Context

Decision 0004 keeps `sources.source` verbatim and carries prefix rules per
target with the table, so the table itself is relocatable: one table serves
public https, GDAL `/vsicurl/` and in situ readers on the HPC system.

The projections are not. Each is rendered for one target with absolute
paths, so a kerchunk or Icechunk store published for THREDDS cannot be read
in place on `/g/data` without rendering it again from the table. Re-rendering
is cheap for us, but a user holding only the published Icechunk or kerchunk
store cannot do it.

Two projection formats can carry the indirection themselves:

- Icechunk named virtual chunk containers (tested with icechunk 2.3.1,
  2026-11-12): a container created with a `name` lets refs be written as
  `vcc://<name>/<rest>`. A reader that opens the repository with a container
  of the same name and its own prefix and store (for example
  `file:///g/data/gb6/` on a local filesystem store) reads in place, with no
  rewrite. Absolute refs cannot be repointed this way: a container's store
  must match the URL scheme (an `https` prefix on a local store is refused),
  and there is no call that rewrites ref locations.
- Kerchunk JSON `templates` (`{{u}}/file.nc`), which 0004 option 3 rejected
  for the table, are the same idea in kerchunk. Kerchunk Parquet has no
  templates. GDAL support for templates is unchecked.

The multidimensional VRT has no equivalent beyond `relativeToVRT`.

What every relocatable projection needs is a stable name for each root that
the per-target rules already imply, so the projection can refer to "root
gb6" instead of one target's URL for it.

## Options

1. **Nothing in the table.** Each renderer derives names (for example a slug
   of the prefix). Works, but two renderers may name the same root
   differently, and a reader has to guess which name to supply.
2. **Optional `root` name on remap rules.** A root is identified by its
   verbatim `prefix`, which every target's rule for it already shares. The
   name is an optional field on those rules; where absent, a fixed slug rule
   gives it. Projections that support indirection use the name.
3. **A separate `roots` table** (`name`, `prefix`) with rules keyed by root
   name. Cleaner normal form, but a breaking change to 0004's rule shape for
   no reader benefit yet.

Evidence: raad.virtualize `py/render_icechunk.py --relocatable`
(mdsumner/raad.virtualize, 2026-11-12) implements option 2, writes
`vcc://` refs for every source under a root, and records the roots in the
root group attribute `byterefs_roots`. A local test rendered for a THREDDS
target and read in place by renaming the container to a local store.

## Decision

Option 2, as proposed:

- A remap rule MAY carry `root`, a name matching `[A-Za-z0-9-]+`. All rules
  with the same `prefix` name the same root; if any of them gives `root`,
  they MUST agree.
- Where no rule for a prefix gives `root`, the name is the prefix with any
  `scheme://` removed, every run of non-alphanumeric characters replaced by
  one `-`, and leading and trailing `-` stripped (`/g/data/gb6/` gives
  `g-data-gb6`). Two prefixes that give the same name are an error.
- A root's prefix for target T is T's `replacement` for it, or the verbatim
  prefix when T has no rule for it.
- A projection that supports indirection (Icechunk named containers,
  kerchunk JSON templates) MAY write paths under a root relative to that
  root's name and SHOULD record, beside the projection, each root's name,
  verbatim prefix and prefix per target, so a reader knows which name to
  map.
- The table is unchanged: `sources.source` stays verbatim, and the
  `byterefs_roots` record is a projection artefact, not a table field.

## Consequences

- Specification: "Remap at publish" gains the optional `root` field, the
  slug rule and the per-target root prefix; a short informative section on
  relocatable projections.
- Schema: remap rule gains optional `root`.
- raad.virtualize: `render_icechunk --relocatable` already follows this;
  the kerchunk writer could emit JSON templates per root (not planned).
- Readers: none required; a reader that ignores `root` still applies the
  rules as in 0004.
- Fixtures: one store with two targets and a named root; the slug rule on
  a local and an https prefix; a name collision that must fail.
- Open: whether relative paths against the table's directory (left open in
  0004) become a special root.
