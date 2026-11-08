#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Check that every number in a written JSON file equals the fixture's.

Usage: check_json_numbers.py EXPECTED.json WRITTEN.json

Exits 0 when both files hold the same structure and every number parses
to the same IEEE 754 double; exits 1 and lists the differences otherwise.
Decision 0010.
"""
import json
import sys


def compare(a, b, where, out):
    if isinstance(a, bool) or isinstance(b, bool):
        if a is not b:
            out.append("%s: %r != %r" % (where, a, b))
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if float(a) != float(b):
            out.append("%s: %r != %r" % (where, a, b))
    elif isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append("%s.%s: present in only one file" % (where, k))
            else:
                compare(a[k], b[k], "%s.%s" % (where, k), out)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append("%s: lengths %d != %d" % (where, len(a), len(b)))
        for i, (x, y) in enumerate(zip(a, b)):
            compare(x, y, "%s[%d]" % (where, i), out)
    elif a != b:
        out.append("%s: %r != %r" % (where, a, b))


def main(argv):
    if len(argv) != 3:
        sys.stderr.write(__doc__)
        return 2
    with open(argv[1]) as f:
        expected = json.load(f)
    with open(argv[2]) as f:
        written = json.load(f)
    out = []
    compare(expected, written, "$", out)
    for line in out:
        print(line)
    print("ok" if not out else "FAILED: %d difference(s)" % len(out))
    return 0 if not out else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
