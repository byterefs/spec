# 0010: Numbers in JSON columns round-trip doubles exactly

- Status: proposed
- Date: 2026-11-08 (proposed)
- Accepted: (date and link to the acceptance pull request, when accepted)
- Closes: issue [#11](https://github.com/byterefs/spec/issues/11)
- Target version: byterefs/0.1

## Context

Two implementations independently truncated BRAN2023 `temp`'s
`scale_factor`, 0.007782219909131527, to 0.0078. Both went through
jsonlite's default of 4 significant digits:

- raad.virtualize, in the R-built BRAN index (fixed with
  `digits = I(17)`);
- zaro, re-serializing consolidated metadata (fixed in zaro 0.0.1.9010).
  Unpacked temperatures were off by up to 0.53 degC.

`digits = NA` in jsonlite gives 15 significant digits, which is not
enough either. For this very value, 15 digits (`0.00778221990913153`)
reads back as a different double. 17 significant digits always round-trip
an IEEE 754 binary64 value.

The table holds numbers as JSON text in `attrs`, `affine` and `codec`, and
as text in `fill`. Nothing in the specification says how precisely they
are written.

## Options

1. **Say nothing**, and leave it to writers. Two writers have already got
   it wrong, silently.
2. **Require exact round-trip** of the double value, and add a fixture
   that catches truncation.
3. **Store numbers as strings** in JSON. That breaks every JSON reader
   that expects CF attributes as numbers.

## Decision (proposed: option 2)

- A number written in a JSON column (`attrs`, `affine`, `codec`), or as
  the text of `fill`, MUST read back as the same IEEE 754 binary64 value
  that was written. Writing 17 significant digits always satisfies this.
  The shortest form that round-trips (as Python's `repr`) is preferred.
- An attribute that is single precision in the source (float32) is
  written as that float32 value converted exactly to a double. For
  example, a float32 0.0078 is written `0.007799999788403511`, not
  `0.0078`. A reader that needs the float32 converts back without loss.
- Integers are written exactly. An integer beyond 2^53 cannot round-trip
  through readers that parse JSON numbers as doubles. Where one can occur,
  the column's definition says how it is written.
- NaN and the infinities are not JSON numbers. This record does not
  decide how they are written in `attrs` or `fill`.

## Consequences

- Specification: one rule under "Rules", and the change listed in
  "Changes from mdim-refs/0.2" with this record.
- Fixtures: `fixtures/json-numbers/` holds an `arrays` row whose `attrs`
  carry 0.007782219909131527 and other values that need 16 or 17
  significant digits. A writer under test re-serializes it, and the
  output must parse to identical doubles.
- Conformance: `conformance/check_json_numbers.py` compares two JSON files
  value by value and fails on any number that differs.
- Implementations: raad.virtualize and zaro already write 17 digits. The
  check should be run against each writer.
