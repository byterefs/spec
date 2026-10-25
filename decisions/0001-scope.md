# 0001: Scope of byterefs

- Status: proposed
- Date: 2026-10-25
- Target version: byterefs/0.1

## Context

byterefs needs a fixed boundary before normative text is written, so that
open questions are argued inside it. The boundary is set out in
[BRIEF.md](../BRIEF.md) section 5.

## Decision

In scope:

- **Reference rows**: chunk key, source, offset, size, presence, inline
  bytes for small chunks.
- **Array description**: dimension names, shape, chunk shape, data type and
  byte order, fill value, codec chain in encode order, packing attributes
  verbatim, and the CF attributes needed to read values correctly.
- **Sources**: identity and integrity (size, modification time, entity tag,
  optionally a checksum).
- **Remap rules**: how a published path is derived from a source for a named
  target.
- **A published encoding**: the Parquet layout a reader can rely on. A
  producer may keep any working encoding; only the published form is
  normative.
- **Conformance**: fixtures, expected tables, and a check.

Out of scope:

- Chunk bytes, beyond inline storage of small chunks.
- Versioning and transactions; byterefs describes one state of the table.
- Catalogues and discovery.
- Georeferencing semantics beyond carrying the source's attributes.
- Rendering to kerchunk, Icechunk, VRT or other forms.

Not yet decided: whether the plan layer is in scope (brief question 6).

## Consequences

The specification describes a table and its published encoding only.
Writers and readers of other forms are implementations, listed in
`IMPLEMENTATIONS.md`, and are not normative.
