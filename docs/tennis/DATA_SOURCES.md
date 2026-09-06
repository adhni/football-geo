# Tennis 2025 data sources

## Scope

This edition freezes the completed 2025 year-end singles top 100 for both tours:

- ATP rankings dated 17 November 2025.
- WTA rankings dated 10 November 2025.
- Exactly 100 players per tour; doubles rankings are excluded.

Ranking points are the official rolling ranking totals at each tour's year-end snapshot. They are not a sum of every point earned during the 2025 calendar year, and raw ATP and WTA totals should be compared within their own tour.

## Sources

- [ATP 2025 year-end rankings release](https://www.atptour.com/en/news/year-end-pif-atp-rankings-2025-release)
- [WTA 2025 year-end numeric singles rankings](https://wtafiles.wtatennis.com/pdf/rankings/RankingArchive/Singles_Numeric_2025.pdf)
- [Tennis Sackmann Archive](https://github.com/Aneeshers/tennis-sackmann-archive) for the machine-readable ranking snapshot, stable player IDs, DOB, handedness, height and represented-country codes. The derived use is attributed under CC BY-NC-SA 4.0.
- [Wikidata](https://www.wikidata.org/) for birthplace entities, coordinates and birth countries.
- [WorldPop Global 2 R2025A](https://hub.worldpop.org/project/categories?id=3) for 2025 population estimates in occupied H3 areas.

## Birthplace resolution

Existing player-to-Wikidata IDs are accepted only when the normalized player name and available DOB agree. Missing IDs are resolved through exact English Wikipedia titles and the same name/DOB checks. Where Wikidata lacks a birthplace, an exact-DOB official ATP/WTA profile may supply the birthplace text and Wikidata supplies only the place coordinates. A player remains in the public QA queue when identity, birthplace, country or coordinates cannot be resolved conservatively.

Ashlyn Krueger remains unresolved because current and archived official WTA profile material disagree between Springfield, Missouri and Dallas, Texas. Neither location is selected until the source conflict can be resolved.

Represented nationality, residence, training base and hometown are never substituted for birthplace.
