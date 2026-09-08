# UFC data notes

## Scope

This edition covers all 42 standard UFC event cards held in calendar-year 2025: 520 completed bouts and 620 unique fighters. Numbered events and Fight Nights are included; Dana White's Contender Series and standalone Road to UFC cards are excluded.

## Measures

- A bout counts once for each participating fighter, producing exactly 1,040 fighter-bout appearances.
- Wins, losses, draws/no contests and finish types come from the completed event result cards.
- UFCStats-derived round totals are available for 515 of 520 fights. The five fights without detailed rows remain in the cohort with result data.
- Significant strikes, takedowns and knockdowns are profile/comparison statistics—not geographic scoring systems.

## Location hierarchy

Verified birthplace is preferred. Exact UFCStats name and date of birth connect a fighter to Wikidata; event-linked English Wikipedia infoboxes are a secondary explicit birthplace source. If birthplace is unavailable, the official UFC profile's **Hometown** field is published as a separately labelled **fighter origin**. It is never presented as birthplace.

Population-normalized H3 layers contain verified birthplaces only. Fighter origins are excluded because a hometown is not a valid population denominator for birthplace production.

## Sources

- [2025 in UFC](https://en.wikipedia.org/wiki/2025_in_UFC) and its linked event result cards — complete event and fight universe (CC BY-SA).
- [UFCStats](http://ufcstats.com/statistics/events/completed?page=all), accessed through a reproducible [UFCStats-derived snapshot](https://github.com/DanMcInerney/mma-ai) — stable fighter IDs, DOB and detailed round totals.
- [Official UFC athlete profiles](https://www.ufc.com/athletes/all) — explicitly labelled hometown fallback.
- [Wikidata](https://www.wikidata.org/) and event-linked English Wikipedia biographies — verified birthplaces and coordinates.
- [WorldPop](https://www.worldpop.org/) 2025 constrained population estimates — birthplace-only H3 population layers.

Raw inputs and retrieval metadata are cached under ignored `data/cache/`. Unresolved fighters remain in the public QA queue.
