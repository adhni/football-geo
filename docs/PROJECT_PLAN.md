# Project Plan

## Question

Which subnational areas produce the most senior international starters for the world's top national teams, both in absolute terms and relative to population?

## V1 analytical unit

`team x season x player x birthplace_admin_area`

The start count is the contribution weight. A player with 60 starts contributes 60; a player with 3 contributes 3.

## Time window

Use 11v11 seasons 1999-00 through 2025-26. In the UI, label this clearly as a season-based historical window. Do not call it exact calendar-year data.

## Cohort

Freeze FIFA top 20 at 20 July 2026. Never dynamically replace this list in V1.

## Data pipeline

### A. Team-season discovery
For each frozen team and season:
- Fetch `https://www.11v11.com/teams/{slug}/tab/players/season/{season_end_year}/`
- Parse player name, profile URL, A, S, goals, position.
- Save raw HTML and parsed parquet.

### B. Player enrichment
For each unique profile URL:
- Fetch profile once.
- Parse DOB, birthplace text, nationality, position.
- Keep raw values.

### C. Birthplace resolution
Resolve player to Wikidata using name + DOB.
- capture player QID
- birthplace QID
- coordinates
- birth country
- confidence / resolution notes

Do not infer birth country from national team.

### D. Administrative assignment
Point-in-polygon against open ADM1/ADM2 geometry.
Store both machine code and display name.

### E. Population
Use one global population methodology across all countries. Preferred public metric denominator: GHSL 2025 for headline comparison. Add 2000/2005/... historical epochs later.

### F. Metrics
Generate:
- team-area totals
- country comparison totals
- foreign-born flows
- period bins
- position splits when reliable

## QA gates

- Duplicate `team-season-player` rows = error unless explicitly explained.
- Negative starts/subs = error.
- Missing birthplace allowed but surfaced.
- Wikidata candidate DOB mismatch = reject.
- Point outside resolved birth country = QA warning.
- ADM1 required for headline metrics; ADM2 may be missing for edge cases.
- Population missing = metric null, never divide by guessed values.

## UI

### World Talent Map
- team selector
- season range
- metric selector: starts / players / starts per million
- domestic / foreign-born toggle

### Country Explorer
- ADM1 choropleth
- click ADM1 -> ADM2 drill-down
- top players behind each area
- raw vs per-capita toggle

### Country Comparison
- concentration index
- top producing ADM1
- foreign-born share
- starts per million

### Generations
Use 5-season bins initially. Upgrade to calendar-year bins after match-level enrichment.

## Non-goals for V1

- academy/development location
- youth internationals
- club career output
- causal claims that birthplace causes football production
