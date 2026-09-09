# Volleyball Nations League 2025 data notes

## Scope

This edition covers the complete 2025 Volleyball Nations League: 116 women's matches and 116 men's matches, including the preliminary phase and Finals. It contains 36 gender-specific national-team entries across 23 countries.

## Measures

- **Players:** unique athletes who entered the court in at least one set.
- **Matches:** matches in which an athlete entered the court.
- **Sets:** sets in which an athlete appeared in the starting rotation, as a substitute or as a libero.
- **Points:** attack points, block points and service aces credited in official match statistics.

The published snapshot contains 580 players, 4,511 player-match appearances, 14,164 player-set appearances and 29,453 player points. Sets are the primary workload measure. Women's and men's results are compared on the same definitions.

## Sources and identity resolution

The official Volleyball World schedule API supplies all match IDs, teams, stages and dates. Each official match centre supplies the all-set scoring table plus per-set starting rotations, substitutions and libero participation. Official player profiles supply full names, dates of birth, positions, heights and sporting nationalities.

Birthplaces require a Wikidata person match verified against the official date of birth. Sporting nationality is never treated as birthplace or birth country. Ambiguous identities and coordinate-less birthplaces remain visible in the QA queue and do not enter population-normalised maps.

The published snapshot verifies coordinates for 349 of 580 players (60.2%). Those players account for 9,230 of 14,164 player-set appearances (65.2%); the remaining 231 players stay visible in the QA queue and are excluded from geographic and population-normalised totals.

## Reproducibility

Raw schedule responses, match fragments and player profiles are cached with retrieval metadata under ignored `data/cache/volleyball_vnl_2025/`. Rebuild with:

```bash
python -m src.ftg.build_volleyball_site --output docs/volleyball/data/dashboard.json --workers 12
```

Generate each committed WorldPop layer by running `src.ftg.build_population_hexes` with H3 resolutions 1, 2 and 3 and the volleyball dashboard input.
