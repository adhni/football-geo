# Codex continuation prompt

You are continuing a football analytics project called **Football Talent Geography**.

Read `README.md`, `docs/PROJECT_PLAN.md`, `docs/DATA_DICTIONARY.md`, and `config/source_registry.csv` before changing code.

## Goal
Build a reproducible dataset and interactive dashboard showing where starters for the FIFA men's top 20 teams (frozen at 20 July 2026) were born, with ADM1/ADM2 drill-down and population-normalised metrics.

## Fixed V1 decisions
- Senior men's A internationals only.
- Frozen top-20 cohort in `config/top20_fifa_2026-07-20.csv`.
- Primary source window: 11v11 seasons 1999-00 through 2025-26.
- Primary contribution metric: **starts** (`A` on 11v11 team-season tables).
- `S` is substitute appearances.
- Do not use arbitrary cap thresholds.
- Birthplace means actual recorded place of birth, NOT club/academy/development location.
- Never infer birth country from national team.
- Preserve provenance and raw source fields.
- Headline population denominator should use one global method, preferably GHSL.
- Published map geometry should prefer open geoBoundaries data.

## Work order
1. Run tests and understand the parser/metric code.
2. Finish a full Italy pipeline across all target seasons.
3. Add raw HTML caching, polite crawl delay, retries and resumability.
4. Enrich unique players with DOB/place-of-birth from profile pages.
5. Add Wikidata resolution using name + DOB; cache results and create manual QA CSV for ambiguous matches.
6. Add geoBoundaries ADM1/ADM2 downloader + point-in-polygon assignment.
7. Add GHSL population ingestion and derive `starts_per_million` / `starters_per_million`.
8. Validate Italy outputs manually before adding other teams.
9. Expand in batches: Spain/France/England/Germany, then remaining top 20.
10. Upgrade Streamlit dashboard to world map + country drill-down + comparison view.

## Quality rules
- Never silently drop unresolved records.
- Never guess coordinates or administrative areas.
- Cache all external responses.
- Keep a `qa/` output with unresolved players, low-confidence Wikidata matches and population join failures.
- Add unit tests for each parser and metric transformation.
- Add coverage statistics by team and season.
- Before claiming a team is complete, compare expected match count vs total starts and document discrepancies.

## Desired final dashboard
- World Talent Map
- Country Explorer (ADM1 -> ADM2)
- Compare Countries
- Generations / 5-season periods
- Metric toggle: raw starters, starts, starters per million, starts per million
- domestic-born / foreign-born toggle
- player detail on hover/click
