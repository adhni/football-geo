# Current data coverage

## Available locally

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

This dataset is a defensible tournament-level fallback. It must not be described as complete national-team coverage from 1999-00 through 2025-26.

## Primary-source limitation

The planned 11v11 team-season endpoint returned HTTP 403 on the one-season smoke test. Collection stopped after two requests. The project does not bypass source access controls.

## Birthplace limitation

The player table includes names, dates of birth and Wikipedia links. Batched Wikipedia/Wikidata birthplace enrichment was paused after repeated HTTP 429 responses, including at a two-second interval. Cached responses are retained for a future courteous resume, but no partial or non-DOB-validated coordinates are published.

## Attribution

The upstream database is © 2023 Joshua C. Fjelstul, Ph.D., licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/), and available from [jfjelstul/worldcup](https://github.com/jfjelstul/worldcup). Derived database outputs must preserve attribution and share-alike terms.
