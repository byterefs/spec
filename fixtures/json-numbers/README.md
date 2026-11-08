# json-numbers

Fixture for decision
[0010](../../decisions/0010-json-numbers-round-trip.md): numbers in JSON
columns round-trip doubles exactly.

`arrays-temp.json` is one `arrays` row written as JSON. Its numbers need
up to 17 significant digits:

- `scale_factor` 0.007782219909131527 is BRAN2023 `temp`. Written with
  15 significant digits it reads back as a different double; written with
  4 (jsonlite's default) it is 0.0078.
- `add_offset` 0.30000000000000004 is 0.1 + 0.2, which needs 17.
- `valid_min_float32` is a float32 0.0078 converted exactly to a double.
- `affine` holds a start and step written with 20 and 17 digits, which
  must read back as the doubles -79.95 and 0.1.

The values are made up for the test, except `scale_factor`.

To test a writer: read `arrays-temp.json`, write it back out with the
writer, then run

    python3 conformance/check_json_numbers.py \
        fixtures/json-numbers/arrays-temp.json written.json

The check passes only if every number parses to the same double.
