# Cricket data notes

## Scope

This edition covers calendar-year 2025 men's and women's T20 internationals in the Cricsheet archive where at least one side is an ICC Full Member. The player cohort contains only players listed for Full Member sides. Finals and other tournament stages are included because the scope is a complete calendar year, not a league regular season; super overs are excluded from performance totals.

The archive produces 175 matches: 123 men's and 52 women's. Those schedules are not equivalent, so raw totals should not be read as a like-for-like comparison of the two competitions.

## Measures

- An appearance is counted once for a listed player in a match, including a replacement recorded in the official team list.
- Batting, bowling and fielding totals come from non-super-over Cricsheet deliveries.
- A ball faced excludes wides. A legal ball bowled excludes wides and no-balls.
- Bowler wickets exclude run outs, retirements, timed out, and obstructing the field.
- Runs conceded exclude byes, leg byes and penalty runs.

## Identity and birthplace

The stable player key is the Cricsheet Register UUID. It connects to the Register's ESPNcricinfo identifier, which is matched to Wikidata property P2697. An exact player name and date of birth may be used only as a fallback identity check. Coordinates come from the stated Wikidata birthplace or, when an already verified player's English Wikipedia infobox explicitly states a birthplace, from that linked place's Wikidata record.

Unresolved players remain in the dataset and QA list. Represented country, nationality, residence, hometown, school, club and development pathway are never substituted for birthplace.

## Sources

- [Cricsheet T20 JSON archive](https://cricsheet.org/downloads/) — match teams and ball-by-ball records.
- [Cricsheet Register](https://cricsheet.org/register/) — stable player identifiers and external ID crosswalk (ODC Attribution licence).
- [Wikidata](https://www.wikidata.org/) and explicit [English Wikipedia](https://en.wikipedia.org/) infobox fields — dates and places of birth.
- [WorldPop](https://www.worldpop.org/) 2025 constrained population estimates — H3 population-normalized layers.

Raw downloads and HTTP responses are cached under ignored `data/cache/`; the committed dashboard records retrieval timestamps and source hashes.
