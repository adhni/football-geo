# Current data coverage

## Live GitHub Pages edition

The published dashboard covers the completed 2025–26 Premier League, La Liga,
Bundesliga, Serie A and Ligue 1 seasons.

- Clubs: 96
- Club-player rows: 2,839
- Unique players with at least one league appearance: 2,690
- Starts: 38,544
- Appearance rows: 54,335
- Lineup QA: every club has exactly `11 × league matches` starts
- Mapped players: 2,423 of 2,690 (90.1%)
- Starts mapped to POB: 37,015 of 38,544 (96.0%)
- Unique mapped birthplace entities: 1,488
- Unresolved POB identities: 267, retained in the QA queue

## Population-normalized map

The per-capita layer groups mapped player birthplaces into H3 resolution-3
cells and divides unique players by each cell's estimated 2025 population.
Population totals come from the WorldPop Global 2 R2025A 1 km population grid.
Only occupied cells are included in the static GeoJSON.

The map displays every occupied cell, but the ranked hotspot list requires at
least two selected players and at least 100,000 estimated residents. Dashed
cells fall below one of those thresholds and should be interpreted cautiously.
The rate describes birthplace production in the dashboard cohort; it is not a
general participation rate or a causal measure of player development.

Identities are resolved through exact Wikidata labels or Wikipedia title
redirects and must match the source birth year. Ambiguous matches are not
published.

## World Cup fallback available locally

The current processed dataset uses the Fjelstul World Cup Database pinned at commit `35a8667f518b07469182ae16d35574dd0e7a00fb`.

- Scope: FIFA men's World Cup finals only
- Tournaments: 2002, 2006, 2010, 2014, 2018 and 2022
- Frozen top-20 teams represented: 19 of 20
- Missing team: Norway, which did not qualify in this window
- Player-tournament rows: 1,839
- Unique players: 1,286
- Team-match appearances: 432
- Starts: 4,752
- Substitute appearances: 1,385
- Lineup QA: every team-tournament has exactly `11 × matches` starts
- DOB-validated POB coordinates: 1,265 of 1,286 players (98.4%)
- Player-tournament rows mapped: 1,812 of 1,839
- Starts mapped to POB: 4,687 of 4,752 (98.6%)
- Unique mapped birthplace entities: 849
- Unresolved POB records: 21 (12 missing Wikidata DOB claims and 9 DOB mismatches)

This dataset is a defensible tournament-level fallback. It must not be described as complete national-team coverage from 1999-00 through 2025-26.

## Primary-source limitation

The planned 11v11 team-season endpoint returned HTTP 403 on the one-season smoke test. Collection stopped after two requests. The project does not bypass source access controls.

## Birthplace coverage

The player table includes names, dates of birth and Wikipedia links. Wikipedia page identities are linked to Wikidata, checked against the source DOB, then joined to Wikidata birthplace coordinates. Only exact DOB matches with valid coordinate ranges are published. The remaining 21 players stay in `data/qa/wikidata_resolution_queue.csv`; the pipeline does not guess their locations.

## Attribution

The upstream database is © 2023 Joshua C. Fjelstul, Ph.D., licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/), and available from [jfjelstul/worldcup](https://github.com/jfjelstul/worldcup). Derived database outputs must preserve attribution and share-alike terms.
