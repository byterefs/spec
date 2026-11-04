# Bytes in place

Status: non-normative note. Living version; dated snapshots may be
published elsewhere (for example the hypertidy blog) and point back here.
Author: Michael Sumner. First full draft 17 Oct 2026; this copy taken
4 Nov 2026 from the working project document.

A position on virtual stores, catalogs and the path from research data to
production. It sits beside three other pieces, and borrows their habit of
stating one stance and arguing it throughout:

- sidebyside (warp and cell: two stances on viewing gridded data),
- regular-in-what (a grid is regular *in a frame*),
- trianglewins (one input contract, many backends, judged by code that
  belongs to none of them).

Two uses. As a **reminder**: section 9 is the list to read before starting
something new. As a **cold drop-in**: sections 1, 5 and 10 stand alone for
someone who has never seen this work.

This copy carries sections 1 to 5, 9 and 10. Sections 6 to 8 (catalog,
production path, tooling) and 11 (open gaps) are operational and stay in
the working project document; references to them below are left as they
are. Text marked **[GAP]** is a question still open for the author.

Nothing here is normative. The specification changes only through decision
records in `decisions/`.

Content is ASCII only.

---

## 1. The stance

> **A virtual store is not a format. It is a table of byte ranges plus a
> plan, and every format is a projection of that table.**

Every array dataset is granules (netCDF, HDF5, GeoTIFF, GRIB) in which each
chunk of each array occupies a byte range. Kerchunk, VirtualiZarr,
Icechunk, a GDAL multidimensional VRT, DMR++ and a COG's tile index all
reduce to knowing those ranges and pointing a reader at them. The tools
disagree about where that knowledge lives: in memory, in a bespoke
manifest, in a transactional repository. This work puts it in one durable,
queryable, language-neutral table and treats each format as a rendering.

Four corollaries follow, and the rest of the piece is them worked out.

1. **Separate what VirtualiZarr fuses.** The concatenation plan (a
   `gdal mdim mosaic` VRT), the byte references (a flat table) and the file
   addressing (source plus remap rules) are three things, held once each.
2. **Endpoints are staged and complementary, not competing.** The mdim VRT,
   a flat Parquet table, kerchunk Parquet and Icechunk each serve a
   different reader and usage model. None is "the" answer and none is
   derived from another; all come from the table.
3. **The catalog points at published forms; it never holds bytes.**
   bowerbird knows how to get non-FAIR data, sds knows the string that opens
   it now, and the byte-ref table sits between them.
4. **Scan once, where it is cheap; reference where it is durable.** Chunk
   offsets are invariant under byte-identical copies, so a scan of a local
   HPC mirror can produce references to a public URL. That is what makes a
   research mirror into a publishing pipeline.

---

## 2. Where it came from: cogcache through blocklist

The idea arrived in pieces, mostly by building something and finding the
same table underneath it. Dates are last commits on each repo's default
branch unless noted.

| When | Piece | What it showed |
|---|---|---|
| May 2025 | mdsumner/zarrquet | VirtualiZarr's kerchunk Parquet is a table of (path, offset, size, raw); "the array key indexes should be in that table as well" |
| Feb 2026 | mdsumner/idea-nci-thredds | the only working VirtualiZarr -> Icechunk on Pawsey; a gotchas guide |
| Mar 2026 | rgdal-dev/cogcache (vwarp vision) | COG tiles fetched by range, decoded in Rust, catalogued in DuckDB; warp as `target_chunk_spec -> {source_chunk_refs} -> read -> warp -> write`, bit-identical to GDAL. "reproject(data, crs) is a mistake." The ref table is already here, as a cache key |
| Mar 2026 | mdsumner/parq2ice | kerchunk Parquet -> Icechunk in Rust; hit flatbuffers ~2 GB on a 16.7M-chunk BRAN array |
| Apr 2026 | mdsumner/pawsey-aad | the Nectar -> Pawsey migration: bowerbird sync into Acacia object storage, COG conversion, VirtualiZarr Parquet, curated listings, all on cron in Singularity |
| Jun 2026 | mdsumner/virtualized | BRAN2023 built twice (blocklist/GDAL and VirtualiZarr), compared |
| Jul 2026 | zarr-icechunk-assure, rema-icechunk, tiny-zlib-oisst-repo | Icechunk 2.1 from tables: OISST in three access cells; 5,800 REMA COGs, ~19.5M refs from rustycogs IFDs |
| Jul 2026 | mdsumner/raad.virtualize | "one central store of byte references, published forms are projections"; 16,387 OISST files scanned in ~20 min into SQLite |
| Jul 2026 | hypertidy/blocklist | the clean split: VRT for logic, rhdf5 chunk walk for physics, kerchunk Parquet out; `access` vs `public` |
| Aug 2026 | mdsumner/aad-filelist | bowerbird dry-run listings as Parquet; a richer SQLite ref schema (arrays, inline, affine) |
| Oct 2026 | mdim-refs/0.2 (this project) | the two SQLite stores merged, column names from GDAL block-info; three readers agree byte for byte on OISST |
| Oct 2026 | wxylib m02, m05 | the table read by Rust into Icechunk (56 tests); then the table as a cache, with held bytes and lineage |

The arc closes on itself: cogcache started as a tile cache keyed by byte
range, and wxylib's m05 design ends as a byte-range cache described by the
same rows. That is evidence for the stance, not a coincidence.

Probably related and not yet read into this project: vrtconcat,
virtual-cog-pilot, rema-ovr, gdal-mdim-summary, sooty, rustycogs' tiff_refs
in detail, hypertidy/rangefinder's Icechunk reader. **[GAP]** Say which of
these belong in the lineage.

---

## 3. Why a table: tabular generality

The case for rows over objects, collected from blocklist, zarrquet,
raad.virtualize and the wxylib cache design.

- **Rows compute without shared state.** Scan per source, in parallel,
  rbind. No live lazy-array graph to serialise between workers; mirai or a
  Slurm array is `map -> rows -> rbind`.
- **Rows are queryable.** With explicit chunk keys (`dim_0..dim_n`) a table
  answers "which chunks touch this box and these days" by predicate
  pushdown before any byte is read. kerchunk's positional index cannot.
- **Rows carry anything.** A per-chunk codec string, a checksum, an mtime,
  inline bytes, a held copy, a spatial bbox, a lineage pointer from a target
  chunk back to its sources. The format does not change when a column is
  added.
- **Rows are language-neutral.** SQLite and Parquet open in R (DBI, arrow,
  duckdb), Python, Rust, GDAL's vector drivers and DuckDB with no shared
  library.
- **Rows make a cache honest.** bowerbird mirrors whole files eagerly; a
  range cache mirrors what was looked at; the same rows describe both, with
  a `held` state (`ref`, `inline`, `copy`, `link`).

The convergent core, found independently in five existing schemas:

```
array, chunk key (explicit), location, offset, length, present
+ array metadata held once (dims, shape, chunks, dtype, fill, codec, attrs)
```

Settled choices in mdim-refs/0.2: explicit keys; chunk rows keyed
*within source* so a rescan is an upsert and the global index is a view;
locations verbatim at scan time with `remap` rules applied at publish;
`size` (block-info) over `length`; byte columns BIGINT; one codec per
array, so a codec change ends an array (eras).

The wider argument is Michael's "Tensors and tables: a map of the layers"
(hypertidy.org, Oct 2026, https://www.hypertidy.org/posts/2026-10-12_tensors-tables/).
Its frame: every dataset is values over an index space plus a map from
index to place, implicit (a recipe) or explicit (stored values); a tensor
is a table whose key is implicit, a table is a tensor whose key is
explicit. "Tensors versus tables" is drawn in a different place by each
of four layers (storage, index, topology, rendering), and storage is the
least fundamental of them. Its closing gap is this piece's thesis in one
line: **byte references are a table that describes a tensor**, the
clearest case of the two sides needing each other rather than competing.
A further consolidation of that story is under way elsewhere.

---

## 4. The model

```
discover   bowerbird / blueant / cmrlifecycle / starc / THREDDS -> sources (access, public, mtime)
plan    A  gdal mdim mosaic                                  -> mdim VRT (Source, SourceSlab, DestSlab)
physical   block-info (GetRawBlockInfo) | rhdf5 walk | DMR++ | TIFF IFDs -> per-source chunk rows
table   B  mdim-refs: sources, arrays, chunk rows, placements, remap -> view refs_<array>
emit       C Icechunk   D kerchunk Parquet   flat Parquet export   OGR layer
publish    Pawsey object storage (truth) -> source.coop, GitHub releases
register   sds row per published form
read       GDAL (Zarr, multidim), gdalraster, GDAL7, ndr, zaro, altarr, robstore, xarray, wxylib
```

Three layers in the table, each held once:

1. **Physical.** For each source and array, the byte range of every chunk,
   keyed by position inside the source. No time, no dataset, no remapping.
2. **Plan.** Where each source's slab sits in the global array, copied from
   the mosaic VRT so the table stands alone outside GDAL.
3. **View.** The global chunk index, `refs_<array>`, exactly the rows
   block-info would emit if run on the mosaic as one array.

The view formula: `dim_i(global) = dim_i(source) - src_offset_i / c_i +
dest_i / c_i`, restricted to chunk-aligned placements. If the mosaic has no
single regular chunk grid it cannot be virtualised, and the table says so
rather than writing a wrong store.

Spec: `byteref/SPEC.md` here; public copy in wxylib/design
`specs/mdim-refs-0.2.md`.

---

## 5. The endpoints, staged and complementary

Each endpoint earns its place by serving a reader the others do not.

| Endpoint | Who reads it | Usage model | Strength | Limit | State (Oct 2026) |
|---|---|---|---|---|---|
| **mdim VRT** | GDAL CLI and API (gdalraster, GDAL7, osgeo.gdal, gdalxarray, ndr) | open one string, GDAL does the rest; also the build plan for the table | day-one R access; inspectable XML; no new format; daily-updated OISST VRT already on Pawsey | serial by source to build; drops some CF attrs (time units); reads go through source files | works; OISST, BRAN, MUR examples |
| **flat Parquet** ("parquet-zarr-lite", see note) | zaro, wxylib, DuckDB, arrow; any range fetcher (robstore) | query the table, fetch only the ranges you need; the cache lives here | pushdown, no codec registry, wasm-friendly, append-only fragments | not a standard; every reader is ours | mdim-refs export read by wxylib; zaro reads the SQLite form (`mdimrefs://`); no flat zarrs reader yet |
| **kerchunk Parquet** | xarray/fsspec, GDAL Zarr driver (`ZARR:"/vsikerchunk_parquet_ref/..."`) | interop with the Python stack and with GDAL as Zarr | widest existing reader base; GDAL reads it today | positional keys; fsspec layout not read by zaro; full rewrite on update | written by blocklist and from mdim-refs; verified on OISST |
| **Icechunk** | xarray/icechunk-python, zarrs, icechunk-js | transactional history: bulk-load once, append days as commits, snapshots in URLs | versioning, checksums against prelim/final churn, browser readers | format moves fast (v1 -> v2 -> v2.1 in a year); ~2 GB manifest limit hit on BRAN (Icechunk 0.3, untested on 2.x with splitting); GDAL reads it only via /vsiicechunk/ in recent builds [to check] | written by wxylib from the table; four older loaders outside R |
| **STAC** (collection + items, stac-geoparquet) | rstac, gdalcubes, sf/arrow/duckdb in R; GDAL STACIT and GTI; pystac, odc-stac, stackstac; STAC Browser; source.coop pages | search and discovery: the collection describes the cube (datacube ext) and points at every other form; items are the source granules | the one form catalogs, browsers and granule-level readers already understand; GTI reads stac-geoparquet directly, so it doubles as the GDAL tile index | an index, not a virtual store: carries no byte ranges; Zarr/Icechunk media types unsettled; items are per granule, so a cube reader still needs a collection asset | raad.virtualize PR #10 (23 Oct 2026): `R/stac.R`, validated, read back by Icechunk, VRT, STACIT, GTI, gdalcubes |
| **SQLite store / OGR layer** | DBI, GDAL vector drivers | the canonical store; inspect with ogrinfo | one file per dataset, no server, publishable read-only | not a reader format | mdim-refs/0.2, OISST 16,387 sources in 14 MB |

Order of building: A and B are the heart; D first among emitters because
blocklist already writes it and GDAL reads it (so R users get it); C as a
sink where versioning matters; the flat Parquet as the place for queries
and cache. C and D may feed back into A as GDAL sources.

Note: "parquet-zarr-lite" (Michael, 19 Oct 2026) is **the flat refs
store between byte-ref harvesting plus metadata collation, and the
virtual-index render** (Zarr or otherwise). It is a middle stage, not a
peer of the renders: harvest and collate into it, render from it. Today
it is the mdim-refs Parquet export (`refs_<array>.parquet` +
`arrays.json`), read directly by wxylib's `wxy-refs` (stage S3c, core
9b486a6, OISST matching GDAL); zaro's enriched-parquet-refs is the same
idea. Its file layout is not fixed yet (one self-describing file with
Parquet key-value metadata is the likely end), and the export still lacks
the `sources` table that cache validation wants.

### Icechunk features as table operations (23 Oct 2026)

Michael's suspicion: much of Icechunk's machinery is a SQL view, or a
simple operation, over a byte-ref table. Checked against the Icechunk 2.x
spec and changelog. The suspicion holds for the *addressing and layout*
features. It does not hold for the *versioning* features, which need real
storage semantics (atomic, conditional writes on object storage); a table
gets those only from a table format that has them.

What the Earthmover side has said on this theme (no direct "it is just a
view" statement found; social posts were not searchable):

- Tom Nicholas and Sebastian Galkin, "Virtual chunks that just work - but
  securely" (10 Jun 2026): virtual chunks "play a similar role that an
  'external table' does in more traditional databases."
  https://tom-nicholas.com/blog/2026/secure-virtual-chunks/
- Tom Nicholas, "Virtual Chunks at Earthmover: From Theory to Production"
  (ESIP Cloud Computing Cluster, 15 May 2026): "The manifest is an
  abstraction layer: you can change the physical layout or the logical
  layout independently of one another", and the logical layer allows cheap
  manipulations like `.shift_array(offset, axis)` or `.move(old, new)`. Its
  format-comparison slide classes LanceDB manifests as *tabular*, with
  transactions and versioning, beside Icechunk, kerchunk and DMR++.
  https://speakerdeck.com/tomnicholas/virtual-chunks-at-earthmover-from-theory-to-production
- Tom Nicholas, GOES-16 post (2 Jun 2026): Icechunk is a "serverless
  transactional cloud-native database for storing chunks."
  https://tom-nicholas.com/blog/2026/virtual-zarr/
- Ryan Abernathey, "Icechunk vs. Iceberg Head-to-Head" (1 Oct 2026):
  Icechunk "borrows the ideas that made Iceberg successful": snapshots,
  transactions, a manifest layer; "Iceberg is tabular, while Icechunk is
  tensor-based." Joe Hamman and Matt Iannucci, "Science data comes in
  tables and tensors" (23 Sep 2026), puts Iceberg tables beside Icechunk
  repos in Arraylake; Zax SQL (15 Sep 2026) maps tensors to relational
  semantics. Michael's tensors-tables post (12 Oct) answers this framing.

The mapping. "View" means a pure function of rows the mdim-refs table
already holds; "layout" means a physical choice about storing the same
rows; "storage" means it needs atomic writes no view can supply.

| Icechunk feature | Table equivalent | Kind |
|---|---|---|
| Virtual chunk container `url_prefix`; 2.0 named containers, refs as `vcc://name/path`; "assets can be relocated ... by just changing the VCCs" | `remap(target, prefix, replacement)` joined at read: longest-prefix match. Icechunk binds late (read), mdim-refs binds at publish | view |
| VCC credentials and read-time authorization | none: a per-prefix access policy, closer to row-level security than to a view | policy |
| `shift_array`, `reindex_array` (regular grids only) | `dim_i + k` over the chunk key: the section 4 placement formula, with the same chunk-aligned restriction | view |
| `session.move` (metadata-only) | update one row of `arrays` (path) | view / one-row update |
| `ChunkRef` (index, location, offset, length), inline, native | `refs_<array>` columns: `dim_*`, `path`, `offset`, `size`, `data`, `present` | same rows |
| Chunk refs sorted by index, binary search | clustered primary key (SQLite `WITHOUT ROWID`) | layout |
| `location_dictionary`, compressed locations | dictionary encoding of `path` (Parquet does it natively) | layout |
| Manifest splitting: non-overlapping `extents` per manifest | partition by `floor(dim_0 / n)`; extents are partition / row-group min-max stats used for pruning | layout |
| `checksum_etag`, `checksum_last_modified`, refuse stale bytes | `sources.mtime` (and an etag column) plus a reader-side check | column + reader policy |
| Diff between commits | `EXCEPT` of two snapshot row sets | view, given snapshots |
| Snapshots, branches, tags, amend | append-only rows with valid-from/valid-to, view "as of"; but publishing that atomically is the hard part | storage |
| Transactions, conflict detection, rebase | the conflict test is set intersection of changed chunk keys per node (the transaction log stores exactly those), a join; the atomic commit is a conditional PUT on the repo ref | storage |
| Expiration, GC | anti-join of reachable vs listed objects; operational, over object storage | storage ops |

Readings, skeptical both ways:

- **Remap is the clearest case, and Icechunk has now built it.** Icechunk
  2.0 named containers are a two-column prefix table resolved at read.
  raad.virtualize `py/render_icechunk.py` resolves remap rules to absolute
  URLs and registers unnamed containers, so a relocation means a re-render.
  Writing `vcc://<target>/<rest>` with one named container per remap row
  would make the Icechunk repo carry the remap table itself, late-bound.
  Small, worth a try; needs Icechunk 2.x on the reader side.
- **Layout features are not free just because they are views.** Splitting,
  sorting and dictionary-coding are where Icechunk spends its engineering
  (flatbuffers, concurrent manifest fetch, binary search across manifests).
  A Parquet table gets the equivalents from Parquet and DuckDB, but only
  for readers that are ours. The ~2 GB BRAN manifest limit was an Icechunk
  layout limit (one manifest), not a table limit; splitting is now in
  render_icechunk (`--split`).
- **Versioning is not a view.** Snapshots-as-views are easy to write and
  wrong without atomic publication: a reader must see one consistent
  snapshot across all arrays, and two writers must not both win. Icechunk
  does this with conditional writes and no server; Iceberg needs a catalog;
  Lance and DuckLake are the table-side options. If the byte-ref table ever
  needs history, borrow a table format with transactions; do not grow one.
  Tom Nicholas (recalled by Michael, source not located): "the only other
  system in the world that uses the same serverless transactional
  mechanism as Icechunk is Lance." Close to true: Lance commits by
  put-if-not-exists of `_versions/{n}.manifest` with optimistic retry, no
  catalog, as Icechunk does with conditional writes. Overstated in one
  respect: Delta Lake's log commit is also put-if-absent and runs serverless
  wherever the store supports it (Azure, GCS, and S3 since conditional
  writes in Aug 2024), though most Delta deployments use a catalog or
  DynamoDB anyway. Iceberg and DuckLake need a catalog. So Lance is the
  natural table-side twin of Icechunk for a versioned byte-ref table.

#### Lance for held bytes: the m16 brief (23 Oct 2026)

wxylib/design m16 (sections 7-8; brief written after Earthmover replied to
Michael in Slack about flatter refs stores), measured on GHRSST MUR 2024
(935,496 refs). Stance: refs until a chunk is needed, then the bytes are
held in the same row; one table covers absent, referenced, inline and held
copy. Lance is the format for the held side: its blob column stores a
value inline or as an external (uri, position, size) range, and
`read_blobs` returns bytes either way. History comes from Lance versions
and tags. SQLite stays the working store; Lance is one more render, later
possibly the store of record for held bytes. Measured: refs-only 10 MB
(56 MB with a full uri per row); taking one held chunk by row 1 ms in
Lance vs 29 ms (Parquet, 64-row groups) and 436 ms (one row group); a
half-held, half-external Hobart window matches GDAL.

What it settles, and what it does not:

- **It answers the held side of gap 10, not the refs side.** Versioning
  pays for itself only where bytes are held: a ref cannot recover bytes
  that changed at the origin, an older Lance tag can. For refs alone the
  history need is mostly a column (sources are immutable, a day is new
  rows), so the thin Parquet layer, or no versioning, still suffices.
- **The Parquet comparison is not the thin-layer comparison.** 1 ms vs
  29 ms is Lance against held bytes inside one Parquet file. A thin layer
  could hold bytes as one object per chunk (Zarr-style) or use the Parquet
  page index; neither was measured. Lance still wins on one table for
  every state and one `read_blobs` call, which is the real argument.
- **Versions must not replace source identity.** "A reprocessed source
  arrives as a new version" is fine for held bytes, but sources stay
  verbatim and immutable (section 9): a reprocessed granule is a new
  source row, and the Lance version records which bytes were held when.
- **No cross-table atomicity.** One commit per table (sources, placements,
  chunks), with readers pinning the chunk-table version, is not
  Icechunk's all-arrays-in-one-commit. Safe while sources and placements
  are append-only; say so in the spec.
- **No key constraint.** Ingest by `merge_insert` upsert on
  (source_id, dim_*); a repeated append duplicates rows. The thin layer
  has the same problem.
- **No https.** Lance object stores read s3/gs/az/file, so source.coop
  needs an s3 twin remap target (`s3://us-west-2.opendata.source.coop/`,
  anonymous). The remap table pays for itself again.
- **R and GDAL: a known gap, accepted.** Michael (23 Oct): "we want the
  best not the best fit everything (yet)". The gap is narrower than the
  brief says: DuckDB 1.5 ships `lance` as a core extension (read, write,
  s3), so R reads Lance rows through the duckdb package. Tested 1 Nov
  (`lance-duckdb/README.md`, DuckDB 1.5.5, extension embedding lance 6.0
  and DataFusion 53.1): plain columns read and `dim_*` filters push down,
  but blob columns (v1 or v2, inline or external) error or segfault, and
  there is no time travel (no version or tag, by path or namespace). So
  R gets the ref side at the latest version only. Workaround: hold copied
  bytes in a plain `large_binary` column, which DuckDB reads; external
  ranges already live in `offset`/`size` plus `sources`/`remap`, so the
  blob type's external form adds nothing a ref row lacks (cost: re-measure
  the 1 ms take). GDAL has no reader. R users keep the VRT and the
  Parquet export.
- **DataFusion lockstep.** Lance's DataFusion provider must match
  DataFusion's major version (lance 13 needs datafusion 54). SedonaDB pins
  its own DataFusion, so this is the concrete question for Arrow/SedonaDB.

Separate, for Icechunk (from the same brief): a repository taking daily
commits should split manifests by the append unit. One year of daily
commits: 22 MB with a 1-day split, 116 MB at 30 days, 1.84 GB at 365.
`render_icechunk.py --split` defaults to 365, which suits one-shot renders
only; an append mode should use 1.
- **Most of what we version is already a column.** Prelim versus final is
  two sources (section 9); a daily append is new rows keyed by source;
  "which granules did this dataset use on date X" is a plan question. That
  covers most of the need Icechunk versioning answers for virtual data, and
  it is why Icechunk stays a sink (section 5), not the store of record.
- **The policy row matters.** VCC authorization exists because a virtual
  ref can point anywhere, including a private bucket. mdim-refs has no
  equivalent; the remap target is the natural place for "allowed prefixes".

### Other index forms, ranked (23 Oct 2026)

Michael asked (23 Oct) for STAC as an output and what else to consider.
STAC is done (PR #10). Ranked by value to R users first, then the
collaborations, with cost. Every one of these is a projection of the same
store plus plan, like the four renders; none needs new harvest.

| Rank | Form | Audience | Cost | Verdict |
|---|---|---|---|---|
| 1 | **STAC collection + items + stac-geoparquet** | rstac, gdalcubes, GDAL STACIT/GTI, pystac, odc-stac, source.coop | done: `R/stac.R`, 44 s for 8,909 items | Render always. |
| 2 | **Root catalog over all datasets** (sds published as STAC, stretch milestone 5) | anyone browsing raad/source.coop; STAC Browser; the production team | small: a `catalog.json` linking each dataset's collection | Next. This, not more per-dataset forms, is what makes the set discoverable. Decide whether sds generates it (section 6, D1 in the reckoning plan). |
| 3 | **GTI (GDAL tile index)** | GDAL CLI/API, gdalraster, terra | zero: GTI opens `stac/items.parquet` directly (verified) | Do not render separately. 2D only (no time axis), so useful for one-time-slice mosaics of COG series and spatial tilings, not for cubes. |
| 4 | **intake-esm datastore** (CSV/Parquet + esmcat JSON) | ACCESS-NRI, CMIP-style xarray users; Charles Turner's intake-virtual-icechunk #67 | small: the items table flattened (path, variable, frequency, start/end) | Do it when Charles confirms the columns, from `items.ndjson`. Python only; no R reader. |
| 5 | **NcML `joinExisting`** | THREDDS (NCI serves BRAN), netCDF-Java, OPeNDAP clients (incl. R via ncdf4/tidync) | small: XML from placements, like the VRT | Only if NCI wants to serve the aggregate. NCI likely has its own BRAN NcML already; check before writing one. |
| 6 | **Discovery metadata** (DCAT / schema.org JSON-LD) | Google Dataset Search, data portals, AADC metadata | tiny, derivable from the STAC collection by existing tools | Leave to the production (source.coop) team. |
| - | **Classic band-stacked VRT for terra/stars** | R raster users | small | Not needed: `terra::rast("mdim.vrt", md = TRUE)` already reads the mdim VRT with time and depth (checked 23 Oct, terra 1.9.50; COG time units fixed in PR #10). |
| - | **DMR++** | Hyrax, NASA | - | An input, not an output: the ready-made physical layer for NASA granules (MUR three-way). Writing DMR++ for non-NASA data serves nobody we serve. |
| - | **mosaicJSON** | titiler web tiles | small | Skip: 2D quadkey index of COGs; titiler reads STAC and GTI. |
| - | **kerchunk JSON, Zarr v3 chunk-manifest proposals** | fsspec | small | Skip: kerchunk Parquet covers the readers; manifest specs are not settled (watch, do not build). |
| - | **OGC EDR / Coverages** | web clients | a server | Out of scope for static publishing. |
| - | **Lance** | DuckDB, Lance readers | - | Already chosen for held bytes; not a consumer-facing index (above). |

Push-back: the forms worth adding are indexes that point at what exists
(STAC, a root catalog, an intake datastore), not more virtual stores. Four
virtual stores already cover GDAL, xarray, query engines and versioned
pipelines; a fifth would add a reader we must verify, not a reader we
gain. The real gaps STAC exposed are in the store: it holds no SRS (the
STAC render reads it from the plan; every other form is CRS-less, terra
guesses lon/lat) and, until PR #10, no time units for COG series.

### Self-describing stores: the adaptive reader note (24 Oct 2026)

Michael's note "self-describing reference stores and adaptive readers"
(virtual-cog-pilot `zarr-explorer`, over the two BRAN2023 kerchunk Parquet
stores in mdsumner/virtualized) proposes a contract: settle what a store
*states* (meaning), leave open how it is *arranged* (layout). That is this
piece's stance from the reader's side, and the explorer's contract tab is
the first working conformance check. Assessed against mdim-refs/0.2
(`byteref/SPEC.md`) and the raad.virtualize renders:

| Note item | Where it already lives | Status |
|---|---|---|
| 1 strict JSON | R writers use `toJSON(digits = I(17), na = "null")`; fill NaN/Inf as strings | met in R renders. Latent: `py/harvest.py` writes `arrays.json` and source sidecars with `json.dump`, which emits bare `NaN` for a NaN nodata; jsonlite should reject it at collate (not run here: no R in this container) |
| 2 chunk-to-row rule | flat store keys every row by `dim_*`: no rule needed | kerchunk-only problem; not stated in our kerchunk render either |
| 3 dims, 8 coords inline, 9 time encoding | `arrays.dims`, `values`/`affine`, CF attrs (time units restored from the scan) | met |
| 4 axis role, 11 orientation, 13 vertical | only as source CF attrs (`axis`, `cartesian_axis`, `positive`) | gap: `arrays` has no dimension type; `mr_write_mdim_vrt` writes `Dimension` with name and size only, dropping the plan's `type`/`direction` (which `R/stac.R` does read) |
| 5 one fill value | `arrays.fill`; kerchunk render sets `fill_value` = `_FillValue` | partly: `missing_value` passes through unchecked |
| 6 packing verbatim | harvest records packing per source; collate stops if it differs | value met; **attribute dtype lost** (float32 `scale_factor` read back as float64 by xarray, see e2e BRAN run) |
| 7 codec chain | `arrays.codec`, one per array, ingest fails on mixed | met |
| 10 provenance | `meta` (dataset, created, generator commit, config, plan), `sources` (full URI set) | mostly met; builder version is a commit, not a release |
| 14 content summary, 15 missing chunks | `present` column; counts logged at collate, not stored | small gap: write counts to `arrays.json`/root attrs |

Defects the note exposes, with causes:

- **scale_factor 0.0078** in the R-built store: already diagnosed. It is
  `blocklist::write_kerchunk_parquet` calling `jsonlite::toJSON()` with the
  default `digits = 4` (comment in `R/mdimrefs_pipeline.R` at the vendored
  copy, and `docs/results.md` item 4). raad.virtualize's renders use 17
  digits; the virtualized store predates that and was never rebuilt. The
  note's "relative error of about 0.23 percent" is right
  (0.0078/0.0077822 - 1). Fix the store (one value in `.zmetadata`, no
  re-harvest) and confirm the blocklist fix landed upstream (unchecked:
  blocklist is outside this project's repo access). A second, separate
  rounding risk: the `gdal mdim mosaic` plan itself keeps an HDF5-driver
  `scale_factor` as reduced-precision text, so GDAL readers of the plan VRT
  alone see a rounded scale. Our renders take packing from the harvest, not
  the plan, and so avoid it.
- **fill -32767 vs -32768** in the VirtualiZarr store: not our code. It
  matters because absent chunks read as Zarr `fill_value` while CF masking
  uses `_FillValue`; if they differ, absent chunks read as valid data
  (-32767 is the bottom of `valid_range`). Worth an upstream issue to
  VirtualiZarr with the BRAN file as the repro.
- **Bare NaN in VirtualiZarr `.zmetadata`**: Python `json` default; same
  class as our latent harvest.py case above.

Push-back on the note:

- **Do not state what the coordinates already say.** Orientation and
  longitude convention (items 11, 12) are derivable from inline
  coordinates; stating them adds a second source of truth that can
  disagree. Keep only what coordinates cannot say: periodic X, and axis
  role where CF attrs are absent.
- **"Exactly one fill value" conflates two things.** Zarr `fill_value`
  (value of an unwritten chunk) and CF `_FillValue`/`missing_value` (mask)
  are distinct concepts; for virtual stores with absent chunks they must be
  *equal*, and that is the rule to state.
- **"Verbatim" packing needs dtype too**, or float32 attributes become
  float64 and xarray decodes to float64.
- **Item 2 is a kerchunk wart, not a contract item.** The flat store and
  Icechunk key chunks explicitly. Better to make the flat store the
  self-describing form and treat kerchunk Parquet as a projection with a
  known convention than to push a root-metadata proposal upstream.
- **The BRAN pair should be labelled fixtures, not converged** (5479 vs
  5844 time steps, different builders): they are the cross-builder test.
  Rebuild only the rounded one.
- **Sidecar `store.json`**: our flat store's `arrays.json` already is one
  (format version, meta, arrays, remap). Extend it with counts and
  dimension roles rather than invent a new file.

Where the checks go: into collate/render (refuse to publish on a conflict),
with the explorer as the external check. Concrete follow-ups, none started:
(a) carry Dimension `type`/`direction` from the plan into `arrays` and back
out in the VRT render; (b) assert `fill_value == _FillValue == missing_value`
in the kerchunk render; (c) `json.dump(..., allow_nan=False)` with NaN as
string in harvest.py; (d) chunk and missing counts in `arrays.json`;
(e) patch `scale_factor` in virtualized `zarr/ocean_temp.zarr`.
Done 24 Oct: (a)-(d) in raad.virtualize PR #11; (e) in virtualized PR #15,
which found salt (0.0017, 1.3 percent), u and v (0.0003, 1.7 percent) also
rounded. jsonlite's `digits = 4` is decimal places, so small values lose
the most.

---


## 9. Reminders for when you diverge

Read this before starting the next exciting thing.

- **Do not write a sixth byte-ref schema.** Five existed; mdim-refs/0.2
  merged two of them. Extend columns, do not fork tables.
- **The VRT is the plan.** `gdal mdim mosaic` is already the n-d
  concatenation engine. Anything that replaces it should read it.
- **Design for time concatenation plus eras first.** Every working example
  (OISST, MUR, BRAN, CDR sea ice) is time-concat; spatial mosaics are
  already GTI's job.
- **Remap at publish, never in sources.** Source URIs are verbatim and
  immutable; prelim and final are distinct sources.
- **A codec change ends an array.** Mixed codecs are an ingest failure, not
  a warning.
- **sds is strings only.** Bytes, tables and caches live elsewhere.
- **R users first.** They are the gap. Day one is the mdim VRT through
  GDAL; next is a table reader; Icechunk is for others.
- **The GDAL PR is yours to write.** Do not let it be generated.
- **Before copying an Icechunk feature, ask: column, view, layout, or
  storage?** Only the last needs a transactional format (section 5,
  Icechunk features as table operations).
- **Icechunk has limits you already hit.** Retest with manifest splitting
  before designing around or away from it.
- **Prove bytes, not structure.** "Opens with the right shape" is not
  "reads the same values as GDAL". The fixtures repo is the habit.
- **Small open loops**: BRAN oracle run on your machine; `scale_factor`
  rounding (0.0078 vs 0.00778...) in the R-built BRAN index; VirtualiZarr
  fill -32767 vs `_FillValue` -32768; GDAL 3.13 GetRawBlockInfo erroring on
  unwritten chunks (worth an upstream issue); zaro's handling of `copy`
  held rows; MUR three-way pilot (DMR++, HDF5 scan, COG IFDs, one table).
- **Composite readers render quietly.** Painting order, SrcRect scaling,
  level substitution and codec unification are rendering decisions fused
  into reads. The store must not express them; they become a plan cut, a
  declared structure (band/zone arrays, chunk edges, a levels relation) or
  a named verb. See `position/quiet-operations.md` (fixtures REMA, COP30,
  Sentinel-2; rema-ovr as a levels relation).

---

## 10. Stretch target (for a cold reader)

Earth observation and ocean model archives are mostly not cloud-native,
and will not be rewritten. They do not need to be. Every chunk of every
array already sits at a known byte range in a file someone is already
serving. Record those ranges once, in a plain table, beside a
concatenation plan GDAL already understands, and the archive can be
published as whatever its readers want: a GDAL VRT for R and GIS users, a
Parquet table for query engines and browsers, kerchunk for xarray, an
Icechunk repository for versioned pipelines. No copies, no new format, and
no single pathway everyone must adopt.

The end state:

- a dataset's knowledge lives in a bowerbird source, its bytes in the
  provider's files, its plan in a VRT, its references in one table, and its
  address in one sds row;
- a daily append is a scan of the new files and an upsert of their rows,
  run where the data is, published to object storage, mirrored to
  source.coop by rule;
- R, Python, GDAL, DuckDB, Rust and the browser read the same table, and a
  conformance fixture proves they read the same values;
- a range cache, described by the same rows, makes repeated access to
  remote archives cheap and records where every derived chunk came from.

Milestones that would demonstrate it, smallest first:

1. OISST daily, all four endpoints from one table, verified (largely done).
2. BRAN2023 (many chunks per file, 4D, many variables, ~16.8M chunks per
   variable) from NCI in situ, byte-verified.
3. MUR SST three ways (DMR++, HDF5 scan, COG mirror) into one table.
4. GDAL block-info merged; gdalraster binding released.
5. sds rows for each published store; the registry published as STAC
   (per-dataset STAC collections render from the store since PR #10; the
   root catalog over them is the next step).

---

