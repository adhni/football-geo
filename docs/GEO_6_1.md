# Geo 6.1 expansion

This branch implements the first expansion release. Published cohorts remain
the committed 2025 / 2025–26 snapshots. New competitions need their own source
validation, participant exports and population layers before publication.

## Explorer changes

- Athletics event selections recalculate entries, rounds and medals from the
  selected event log. Team charts use the same participant filters as maps.
- Shared explorers offer age filters when ages are available. Ranking editions
  also offer top-25, top-50 and top-100 subsets within the published cohort.
- Performance measures expose existing source totals on birthplace and country
  maps: cricket runs/wickets, motorsport podiums, athletics medals, volleyball
  attack/block/serve points, and available league statistics. Team selections
  use only the matching contribution splits. Population measures retain their
  documented participant and primary-workload definitions.
- AFL/UFC coverage distinguishes mapped locations from verified birthplaces.

## Languages

English, Spanish, French, Arabic and Indonesian were moved to stable message
catalogs. Portuguese, German and Italian are explicitly labelled previews:
core controls and dynamic templates are translated; longer descriptions fall
back to English. Country names use the selected locale. Athlete and city names
retain their source identities. Shared links can specify `?lang=pt`, `de` or
`it`; a supported URL choice takes precedence over the saved preference.

Edit `config/locales/index.json` for language names, locales and directions.
Edit each language's JSON for messages. The runtime uses stable message keys;
English phrase matching remains as a compatibility bridge for existing pages.
Complete catalogs must cover every English key. Previews may omit descriptive
copy, but must cover all dynamic templates and count messages. Generation
checks interpolation parameters and rejects empty or unknown messages.

## Edition configuration

`config/editions.json` separates sport identity from competition editions:
NBA is a basketball edition, NFL an American-football edition, UFC an MMA
edition. Existing URLs and data identities are retained. Renderer settings live
in this configuration; generated inline page settings are build artifacts.

The generated `docs/assets/edition-catalog.js` combines configuration with the
actual dashboard scope, period, grouping, participant counts and coverage.
It validates coordinates, duplicate contributions and summary totals. A
birthplace can have missing display labels while retaining valid coordinates;
the validator preserves that existing data contract.

After changing configuration, messages or a published snapshot:

```bash
make catalogs PYTHON=.venv/bin/python
make test PYTHON=.venv/bin/python
```

`make test` checks that generated catalogs and page settings are current.

Browser validation covered all 17 explorers, event/ranking/performance filters,
language switching and mobile controls. The existing CARTO basemap endpoint
displayed an "API key required" tile during local inspection; athlete overlays
rendered. The subsequent basemap fix switches all maps to OpenStreetMap through
`docs/assets/basemap.js`; see [development notes](DEVELOPMENT.md#map-background).

## Broader tennis cohorts

The builder now accepts an exact top N and explicit ATP/WTA ranking dates.
Both dates must fall in the same year. Arbitrary dates are labelled ranking
snapshots; only the original verified 2025 dates are called year-end rankings.
Age is calculated at the later selected ranking date.

The [top-250 tennis edition](tennis-250/) now publishes 500 players on the same
2025 year-end dates, with an edition selector linking it to the original
top-100 view. It includes all three rebuilt population layers and a public
[coverage/QA report](tennis-250/DATA_SOURCES.md).

```bash
python -m src.ftg.build_tennis_site \
  --limit 250 \
  --atp-ranking-date 20251117 --wta-ranking-date 20251110 \
  --output data/processed/tennis_top250_2025.json
```

The existing `--atp-rankings-input`, `--atp-players-input` and corresponding WTA
options support local source CSVs, including ranking archives outside the
default 2020s files. Each selected ranking must contain exactly ranks 1–N;
incomplete snapshots fail. Custom cohorts cannot overwrite the published
tennis JSON. Source attribution and existing noncommercial/share-alike terms
still apply. Rebuild H3 layers at resolutions 1–3 for any new published cohort.

## Broader cricket cohorts

The builder supports explicit calendar years, T20/ODI/Test match types, Full
Member-only or all international sides, and explicitly supplied club archives.
Multi-day matches are assigned to the year of their first recorded date.
Appearances count once per match; batting innings and delivery totals retain
their own definitions. Super overs remain excluded from performance totals.

```bash
python -m src.ftg.build_cricket_site \
  --year 2025 --match-type ODI --include-associates \
  --output data/processed/cricket_odi_2025.json

python -m src.ftg.build_cricket_site \
  --year 2025 --team-type club --include-associates \
  --archive-input data/cache/ipl_json.zip \
  --output data/processed/cricket_ipl_2025.json
```

Download the appropriate competition archive from Cricsheet for club builds.
Club names never become inferred player nationalities. Archive coverage does
not imply complete coverage of all matches. Custom cohorts require separate
outputs and birthplace caches; population membership must be rebuilt before
publication.

## Table-tennis pilot

`src.ftg.build_table_tennis_site` imports an explicitly sourced men's/women's
singles ranking cohort. It is not registered as a published edition. The ITTF
2025 archive returned HTTP 403 during inspection, so this release uses local
inputs rather than bypassing access controls or inventing a ranking snapshot.

Use `config/table_tennis_rankings_template.csv`. Columns are `ranking_date`
(ISO date), `event` (`MS`/`WS`), `rank`, numeric WTT `player_id`, `name`,
`represented_country`, `points`, and optional `dob` (ISO date). Supply both
singles groups with exactly ranks 1–N on one date. Doubles are excluded until
pair-point allocation and deduplication rules are implemented.

```bash
python -m src.ftg.build_table_tennis_site \
  --rankings-input data/incoming/table_tennis_rankings.csv \
  --ranking-date 2025-12-23 --limit 100 \
  --source-url https://www.ittf.com/2025-ittf-table-tennis-world-ranking/ \
  --output data/processed/table_tennis_pilot.json
```

Optional `--birthplaces-input` accepts JSON keyed by WTT player ID. Each
location must include a matching `source_player_id`, `wikidata_qid`, a
documented `source_url`, birthplace `place`/`country`, valid `lat`/`lon`, and a
matching `dob` if the ranking input supplies one. Resolve identity through
Wikidata's World Table Tennis player ID property P1364. This is a curated
verified-location input contract, not an automatic identity resolver. Missing
or rejected locations remain in participants, totals and public QA. Nationality
is never used as a birthplace.

Before publication: acquire and attribute a real ranking snapshot, verify its
location input, review coverage, create its explorer configuration/page, and
build the three population layers. No empty or synthetic pilot is advertised
in the sport directory.
