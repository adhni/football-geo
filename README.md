# Talent Geography

A reproducible data + visualisation project that started with football and now
includes cricket, tennis, padel, badminton, golf, AFL, NRL, NBA, NFL, NHL and MLB editions in the same public site.

The football project asks:

> **Where do the world's leading men's national teams actually get their starters from, and which places over-produce elite footballers relative to population?**

The live GitHub Pages edition currently maps all **2,690 players who made at
least one appearance in the 2025–26 Premier League, La Liga, Bundesliga, Serie
A or Ligue 1**. It covers 96 clubs and keeps unresolved birthplace identities
visible for QA.

The interface includes clustered birthplace points, a country choropleth, a
WorldPop-normalised local hotspot layer, five-league geographic comparisons,
age distributions and clickable player profiles.

## Frozen cohort

The project freezes the **FIFA men's top 20 at 20 July 2026** so results do not change every time FIFA updates its ranking. The cohort is stored in `config/top20_fifa_2026-07-20.csv`.

## V1 scope

- Men's senior A internationals
- Top 20 teams frozen at 2026-07-20
- Seasons **1999-00 through 2025-26** as the reproducible source window
- Primary weight = **starts**, not arbitrary cap thresholds
- Secondary measures = unique starters, substitute appearances, total appearances
- Geography = birthplace point -> ADM1 and ADM2
- Population-normalised metrics using a globally consistent population source

Why season-based? 11v11 exposes national-team squad statistics with `A` (starts) and `S` (substitute appearances) consistently by season. This lets V1 cover 20 countries across ~26 years without requiring every individual match sheet. Exact calendar-date lineups can be added later.

## Core metrics

For each team / geography / period:

- `unique_starters`
- `starts`
- `competitive_starts`
- `sub_appearances`
- `starts_per_million`
- `unique_starters_per_million`
- domestic-born vs foreign-born share
- concentration / HHI across producing areas

## Source strategy

See `config/source_registry.csv`.

1. **11v11** — season player start/sub counts and player profile birthplace text.
2. **Wikidata** — birthplace entity, coordinates and birth country; resolved by player name + DOB and cached.
3. **geoBoundaries** — open ADM1/ADM2 map geometry for published visualisations.
4. **WorldPop Global 2** — 2025 local population totals for the live H3 hotspot map.
5. **GHSL / GHS-POP** — planned historical population denominator for 5-year epochs.
6. **OpenFootball internationals** — match-universe validation.

Raw HTML and external datasets should be cached locally but not committed unless their terms allow redistribution.

## Quick start

Python 3.10 or newer is recommended.

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt

# Test the parser + metric engine
pytest -q

# Build the seeded demo outputs
python -m src.ftg.build_demo

# Launch the demo dashboard
streamlit run dashboard/app.py
```

## GitHub Pages dashboard

The public, backend-free dashboard lives in `docs/` and is served directly by
GitHub Pages. The football explorer lives at `/`, the cricket explorer at
`/cricket/`, the tennis explorer at
`/tennis/`, the padel explorer at `/padel/`, the badminton explorer at
`/badminton/`, the golf explorer at `/golf/`, the AFL explorer at `/afl/`, the
NRL explorer at `/nrl/`, the NBA explorer at `/nba/`, the NFL explorer at `/nfl/`, the NHL explorer at
`/nhl/` and the MLB explorer at `/mlb/`, with a sport switcher shared between
them. To
refresh the football data and preview every edition locally:

```bash
python -m src.ftg.export_static_site
python -m src.ftg.build_population_hexes \
  --output docs/data/population_hexes_r3.geojson \
  --h3-resolution 3 --use-rasters
python -m http.server 8000 --directory docs
```

Then open `http://localhost:8000`. The generated dashboard data is committed at
`docs/data/dashboard.json`; raw and intermediate datasets remain local.
The population command queries only occupied H3 cells and resumes from the
ignored `data/cache/` checkpoint.

To refresh the calendar-year 2025 men's and women's T20I snapshot:

```bash
python -m src.ftg.build_cricket_site \
  --archive-input data/cache/cricket_2025/t20s_json.zip \
  --register-input data/cache/cricket_2025/people.csv \
  --output docs/cricket/data/dashboard.json --workers 12
python -m src.ftg.build_population_hexes \
  --input docs/cricket/data/dashboard.json \
  --output docs/cricket/data/population_hexes_r3.geojson \
  --cache data/cache/cricket_worldpop_population_2025.json \
  --h3-resolution 3 --use-rasters
```

The cricket builder selects players representing ICC Full Member sides from
Cricsheet's 2025 T20 international archive. It counts each listed player once
per match, excludes super overs from performance totals, and links the stable
Cricsheet UUID through ESPNcricinfo IDs to verified birthplace data. See
`docs/cricket/DATA_SOURCES.md` for the precise scope and stat definitions.

To refresh the completed 2025 AFL home-and-away snapshot:

```bash
python -m src.ftg.build_afl_site \
  --stats-input data/cache/afl_afltables_player_stats.parquet \
  --output docs/afl/data/dashboard.json \
  --wikidata-cache data/cache/afl_wikidata_2025.json
python -m src.ftg.build_population_hexes \
  --input docs/afl/data/dashboard.json \
  --output docs/afl/data/population_hexes_r3.geojson \
  --cache data/cache/afl_worldpop_population_2025.json \
  --h3-resolution 3 --use-rasters
```

The AFL builder keeps numeric rounds only, validates all 18 clubs, preserves
club splits, and resolves verified birthplaces from Wikidata or explicit English
Wikipedia infobox fields. When birthplace is unavailable, it uses a separately
labelled, DOB-verified Wikipedia `originalteam` fallback and resolves the club's
documented base or venue. Population layers remain verified-birthplace-only.
See `docs/afl/DATA_SOURCES.md` for scope, coverage, and attribution.

To refresh the completed 2025 NRL regular-season snapshot:

```bash
python -m src.ftg.build_nrl_site \
  --competition-id 12755 \
  --output docs/nrl/data/dashboard.json \
  --workers 8
python -m src.ftg.build_population_hexes \
  --input docs/nrl/data/dashboard.json \
  --output docs/nrl/data/population_hexes_r3.geojson \
  --cache data/cache/nrl_worldpop_population_2025.json \
  --h3-resolution 3 --use-rasters
```

The NRL builder reads all 204 Champion Data match files, excludes period rows
and unused zero-stat reserves, preserves club splits, and resolves exact-name
Wikidata identities explicitly classified as rugby league players. See
`docs/nrl/DATA_SOURCES.md` for scope and attribution.

To refresh the completed 2025 tennis year-end snapshot:

```bash
python -m src.ftg.build_tennis_site
python -m src.ftg.build_population_hexes \
  --input docs/tennis/data/dashboard.json \
  --output docs/tennis/data/population_hexes_r3.geojson \
  --cache data/cache/tennis_worldpop_population_2025.json \
  --h3-resolution 3 --use-rasters
```

The tennis builder freezes exactly the ATP and WTA singles top 100 at their
official 2025 year-end ranking dates. It preserves rank and ranking points,
uses stable player IDs and DOB checks for birthplace resolution, and keeps
unresolved players in public QA. See `docs/tennis/DATA_SOURCES.md` for scope,
ranking semantics and attribution.

To refresh the completed 2025 FIP padel ranking snapshot:

```bash
python -m src.ftg.build_padel_site
python -m src.ftg.build_population_hexes \
  --input docs/padel/data/dashboard.json \
  --output docs/padel/data/population_hexes_r3.geojson \
  --cache data/cache/padel_worldpop_population_2025.json \
  --h3-resolution 3 --use-rasters
```

The padel builder freezes 100 men and 100 women from the final 2025 FIP
individual ranking. Official FIP profiles supply DOB and birthplace text;
GeoNames supplies coordinates. Region-only birthplaces remain in public QA.
See `docs/padel/DATA_SOURCES.md` for the women's carry-forward snapshot note,
resolution method and attribution.

To refresh the 30 December 2025 BWF badminton ranking snapshot:

```bash
python -m src.ftg.build_badminton_site
python -m src.ftg.build_population_hexes \
  --input docs/badminton/data/dashboard.json \
  --output docs/badminton/data/population_hexes_r3.geojson \
  --cache data/cache/badminton_worldpop_r3.json \
  --h3-resolution 3 --use-rasters
```

The badminton builder freezes the top 100 men's and women's singles players
plus the top 50 men's, women's and mixed doubles pairs. Pair points are divided
equally between partners for geography, while athletes are deduplicated by BWF
ID across events. See `docs/badminton/DATA_SOURCES.md` for ranking-week
semantics, birthplace resolution and attribution.

To refresh the final 2025 golf world-ranking snapshot:

```bash
python -m src.ftg.build_golf_site
python -m src.ftg.build_population_hexes \
  --input docs/golf/data/dashboard.json \
  --output docs/golf/data/population_hexes_r3.geojson \
  --cache data/cache/golf_worldpop_r3.json \
  --h3-resolution 3 --use-rasters
```

The golf builder reads the official OWGR Week 52 PDF and WWGR 29 December CSV,
validates an exact top 100 from each ranking, and preserves total points,
average points and events played. See `docs/golf/DATA_SOURCES.md` for the
separate-system comparison rule and birthplace methodology.

To refresh the NBA snapshot:

```bash
python -m src.ftg.build_nba_site
python -m src.ftg.build_population_hexes \
  --input docs/nba/data/dashboard.json \
  --output docs/nba/data/population_hexes_r3.geojson \
  --cache data/cache/nba_worldpop_population_2025.json \
  --h3-resolution 3 --use-rasters
```

The command downloads a public NBA Stats API export, joins players to recorded
Wikidata birthplaces through NBA.com player IDs and writes
`docs/nba/data/dashboard.json`. See `docs/nba/DATA_SOURCES.md` for scope and
attribution.

To refresh the snap-defined NFL snapshot:

```bash
python -m src.ftg.build_nfl_site
python -m src.ftg.build_population_hexes \
  --input docs/nfl/data/dashboard.json \
  --output docs/nfl/data/population_hexes_r3.geojson \
  --cache data/cache/nfl_worldpop_population_2025.json \
  --h3-resolution 3 --use-rasters
```

This joins nflverse regular-season snap counts to ESPN birth-city fields and
GeoNames coordinates. Players without a conservative city match remain in the
published QA queue. See `docs/nfl/DATA_SOURCES.md` for scope and attribution.

To refresh the NHL snapshot:

```bash
python -m src.ftg.build_nhl_site
python -m src.ftg.build_population_hexes \
  --input docs/nhl/data/dashboard.json \
  --output docs/nhl/data/population_hexes_r3.geojson \
  --cache data/cache/nhl_worldpop_population_2025.json \
  --h3-resolution 3 --use-rasters
```

This reads exact per-team skater and goalie totals plus recorded birthplaces
from the NHL public API, then matches coordinates conservatively through
GeoNames. See `docs/nhl/DATA_SOURCES.md` for scope and attribution.

To refresh the MLB snapshot:

```bash
python -m src.ftg.build_mlb_site
python -m src.ftg.build_population_hexes \
  --input docs/mlb/data/dashboard.json \
  --output docs/mlb/data/population_hexes_r3.geojson \
  --cache data/cache/mlb_worldpop_population_2025.json \
  --h3-resolution 3 --use-rasters
```

This reads exact per-team hitting and pitching lines plus recorded birthplaces
from the official MLB Stats API. Workload is plate appearances plus batters
faced. See `docs/mlb/DATA_SOURCES.md` for scope and attribution.

For each sport, run its population command at H3 resolutions 1, 2 and 3 to
refresh the Very broad, Large, and Regional area sizes. The layers use cached
official WorldPop country rasters because the public polygon API limits
requests to 50,000 km². Each sport and area size derives a stable colour scale
from its full unfiltered population-rate distribution.

To rebuild the current Big Five edition:

```bash
python -m src.ftg.import_top5
python -m src.ftg.enrich_top5_wikidata
python -m src.ftg.build_top5
python -m src.ftg.export_static_site \
  --input data/processed/top5_players_with_birthplace.parquet \
  --unresolved data/qa/top5_wikidata_resolution_queue.csv
```

## Importing the 20-team dataset

Place CSV or Parquet files in `data/incoming/`, then run:

```bash
python -m src.ftg.import_data --input data/incoming
```

The importer accepts split files, normalises common source headings, validates the frozen cohort and season window, prevents duplicate team-season-player rows, and writes coverage/issue reports to `data/qa/`. See `docs/INCOMING_DATA.md` and `config/incoming_player_seasons_template.csv` for the contract.

## Full collection flow

```bash
# Option A: scrape all team-season squad tables politely and cache HTML
python -m src.ftg.collect_11v11 --start-season 2000 --end-season 2026

# Option B: import prepared CSV/Parquet files
python -m src.ftg.import_data --input data/incoming

# Bounded open-data fallback: World Cup finals, 2002-2022
git clone --depth 1 https://github.com/jfjelstul/worldcup.git /tmp/ftg-worldcup
python -m src.ftg.import_worldcup --source-dir /tmp/ftg-worldcup/data-csv

# 2) Build unique player table + fetch player profile metadata
python -m src.ftg.enrich_players

# 3) Resolve birthplace coordinates / birth country with Wikidata
python -m src.ftg.enrich_wikidata

# 3b) Build point-map inputs and birthplace coverage QA
python -m src.ftg.build_birthplaces

# 4) Spatially join birthplace points to ADM1/ADM2
python -m src.ftg.assign_admin --adm1 path/to/adm1.geojson --adm2 path/to/adm2.geojson

# 5) Join population table and calculate final metrics
python -m src.ftg.build_metrics --population data/raw/population_admin.csv
```

## Important data rule

**Birthplace is not academy/development location.** A player is credited to the administrative area containing their recorded birthplace. A future extension can separately model youth-development geography.

## Reproducibility / QA

Every record should retain:

- source URL
- retrieval timestamp
- raw source field
- resolved player ID
- birthplace confidence
- ADM assignment method
- population source + epoch

Machine-readable validation and coverage reports are written to `data/qa/`; unresolved records remain visible there and are never silently discarded.

Do not silently force ambiguous players or birthplaces. Put unresolved rows into QA outputs.

## Seed data

`data/seed/italy_2005_06_11v11.csv` is a real seed extracted from the Italy 2005-06 national-team season page and demonstrates the start/sub structure. `data/seed/italy_2006_final_starters.csv` is a small visual demo of the World Cup Final XI birthplaces.

## Current open-data fallback

If the primary all-international source is inaccessible, `import_worldcup` builds a clearly labelled match-level dataset from the Fjelstul World Cup Database. It covers the 2002, 2006, 2010, 2014, 2018 and 2022 men's World Cup finals. This is not equivalent to complete national-team seasons: non-qualifiers have no rows and qualifiers include finals matches only.

The upstream database is © 2023 Joshua C. Fjelstul, Ph.D., licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/), and sourced from [jfjelstul/worldcup](https://github.com/jfjelstul/worldcup). Derived database outputs must retain that attribution and share-alike license.

See `docs/CURRENT_COVERAGE.md` for exact row counts, validation results and current source limitations.

## Recommended next milestones

1. Complete Italy 1999-00 → 2025-26 end-to-end.
2. Validate summed season starts against match counts (`11 * matches`, allowing unusual match records/coverage flags).
3. Add Spain, France, England, Germany as the first cross-country batch.
4. Expand to all frozen top 20.
5. Add historical population epochs and period slider.
6. Add match-level competitive/friendly classification where exact dates are needed.
