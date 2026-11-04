# Notes

Non-normative writing behind the specification: positions, musings and
the reasoning that later decisions draw on. Nothing here changes the
specification; that happens only through a record in `decisions/`.

Notes are living documents, changed by pull request like everything else.
A blog post or talk that draws on one should be a dated snapshot that
links back here.

| Note | What it is |
|---|---|
| [bytes-in-place.md](bytes-in-place.md) | the position: a virtual store is a table of byte ranges plus a plan, and every format is a projection of it |
| [quiet-operations.md](quiet-operations.md) | musing: what composite raster readers do silently (painting, resampling, level substitution), the hidden / declared / separated ladder, and the REMA, COP30 and Sentinel-2 fixtures |
