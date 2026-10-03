# Development and rebuilds

## Layout

See [Geo 6.1 expansion](GEO_6_1.md) for catalog generation, language previews,
configurable tennis/cricket cohorts and the table-tennis import pilot.

| Location | Responsibility |
| --- | --- |
| `src/ftg/build_*_site.py` | Sport-specific source parsing, cohort rules, aggregation and export |
| `config/editions.json` | Sport/edition identities and shared explorer settings |
| `config/locales/` | Language metadata and stable message catalogs |
| `src/ftg/build_edition_catalog.py`, `build_language_catalog.py` | Validate and generate static catalog assets and page wiring |
| `src/ftg/utils.py` | Atomic JSON replacement, cached binary download, ASCII lookup keys and age calculation |
| `src/ftg/geonames.py` | GeoNames inputs, city indexes and existing country/state matching policies |
| `src/ftg/wikidata_birthplaces.py` | Shared name/title lookup with exact DOB validation, used by MotoGP and volleyball |
| `src/ftg/http_cache.py` | Text responses, request retries and retrieval metadata |
| `src/ftg/build_population_hexes.py` | Birthplace-only population denominators and H3 exports |
| `docs/assets/league-app.js` | Shared sport explorer, configured by each page's `TALENT_GEO_EDITION` |
| `docs/assets/app.js`, `docs/nfl/app.js` | Football and NFL explorers with their distinct data models |
| `docs/compare/compare.js` | Cross-sport map comparison |
| `docs/assets/basemap.js` | Shared tile provider and attribution for all maps |

Keep source-specific assumptions in the sport builder. Shared helpers must not
import sport builders. Their imports are re-exported from existing builders for
compatibility, but new consumers should import the shared module directly.

Age helpers require an explicit date; the short wrappers in each builder retain
that sport's frozen snapshot date. Formula, MotoGP and volleyball retain their
special transliteration rules. Volleyball also retains its stricter DOB parser.
GeoNames matching policies were moved without changing ambiguity handling.
The shared Wikidata lookup retains the historical `motogp_*` raw cache group
names so existing cached responses remain usable by both callers.

## Map background

All explorers, comparison panels and athlete profile maps use the provider in
`docs/assets/basemap.js`. The default is OpenStreetMap's standard HTTPS tile
service, which does not require a key. A CSS filter on the dark tile layer
matches the interface; population modes use the original light tiles. Filters
do not affect athlete markers, country shapes or population overlays.

Keep linked OpenStreetMap attribution visible, including on profile maps.
Requests use the browser's cache and a valid referrer. Fetch tiles only for
interactive viewing, without prefetching or offline downloads. The public
service is best-effort; if traffic grows, change the shared provider to a
service with appropriate capacity and update its attribution. See the
[tile usage policy](https://operations.osmfoundation.org/policies/tiles/).
Automated browser tests should substitute local tile fixtures rather than
pan or zoom against the public tile service.

## Tests

Activate the Python environment, install `requirements.txt`, and install Node.js
22 or newer. Run both suites with:

```bash
make test
# Or, without activating the Python environment:
make test PYTHON=.venv/bin/python
```

`make test-python` runs pytest. `make test-js` uses Node's built-in test runner;
there is no npm dependency or browser installation required. The clipboard
tests execute the production event handler with real EventTarget dispatch and a
controlled asynchronous clipboard, while substituting map bootstrapping. They
cover both successful and rejected clipboard requests, not Leaflet rendering.
GitHub Actions runs both suites on pushes and pull requests.

Add behavior tests around changed parsing, aggregation, export or cache rules.
Source-string checks in `test_static_map_explorer.py` remain useful for asset
wiring but do not establish that an interaction or calculation works.

## Rebuild boundaries

`make preview` serves committed snapshots without changing data.
`make rebuild-football` executes import, enrichment, export and all three
population layers for the Big Five edition. It requires external sources and
can download large population rasters. The exporter defaults to Big Five inputs
and protects the live dashboard path against other cohorts and seasons.

Historical World Cup and incomplete 11v11 collection instructions are separate
in the [README](../README.md#historical-world-cup-flow). Historical exports use
an explicit output path and are not directly supported by the Big Five UI.

After changing dashboard records, rebuild population layers at H3 resolutions
1, 2 and 3: their player ID membership must match the new snapshot. Reusing a
cached population total never reuses the old player membership.

Raster totals are cached separately from polygon API totals. Changes to year,
H3 cell, WorldPop release, country geometry, country aliases, raster directory
or country hints produce distinct cache keys. The raster algorithm's `v1`
namespace must be bumped when calculation semantics change. Manual edits to
cached raster files require `--refresh-population`; content hashes of large
raster files are deliberately not recalculated on each build.

Use a single writer for each cache path. The JSON writer atomically replaces
files; it does not coordinate simultaneous processes writing the same cache.
