# Football Talent Geography

A reproducible data + visualisation project that asks:

> **Where do the world's leading men's national teams actually get their starters from, and which places over-produce elite footballers relative to population?**

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
4. **GHSL / GHS-POP** — consistent population denominator, including historical 5-year epochs.
5. **OpenFootball internationals** — match-universe validation.

Raw HTML and external datasets should be cached locally but not committed unless their terms allow redistribution.

## Quick start

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

## Full collection flow

```bash
# 1) Scrape all team-season squad tables politely and cache HTML
python -m src.ftg.collect_11v11 --start-season 2000 --end-season 2026

# 2) Build unique player table + fetch player profile metadata
python -m src.ftg.enrich_players

# 3) Resolve birthplace coordinates / birth country with Wikidata
python -m src.ftg.enrich_wikidata

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

Do not silently force ambiguous players or birthplaces. Put unresolved rows into QA outputs.

## Seed data

`data/seed/italy_2005_06_11v11.csv` is a real seed extracted from the Italy 2005-06 national-team season page and demonstrates the start/sub structure. `data/seed/italy_2006_final_starters.csv` is a small visual demo of the World Cup Final XI birthplaces.

## Recommended next milestones

1. Complete Italy 1999-00 → 2025-26 end-to-end.
2. Validate summed season starts against match counts (`11 * matches`, allowing unusual match records/coverage flags).
3. Add Spain, France, England, Germany as the first cross-country batch.
4. Expand to all frozen top 20.
5. Add historical population epochs and period slider.
6. Add match-level competitive/friendly classification where exact dates are needed.
