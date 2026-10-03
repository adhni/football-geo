# Tennis top 250: 2025 year-end edition

This edition contains exactly ranks 1–250 in each singles list: 250 ATP players
on 17 November 2025 and 250 WTA players on 10 November 2025. It adds 300 players
to the separate [top-100 edition](../tennis/). Doubles are excluded. Age is
calculated at 17 November 2025, matching the existing edition.

## Sources and verification

- [Jeff Sackmann's ATP data](https://github.com/JeffSackmann/tennis_atp) and
  [WTA data](https://github.com/JeffSackmann/tennis_wta), through the
  [Tennis Sackmann Archive](https://github.com/Aneeshers/tennis-sackmann-archive):
  dated rankings, stable player IDs, names, DOB and represented-country codes.
  Credit Jeff Sackmann. Derived ranking data is **CC BY-NC-SA 4.0**.
- [ATP 2025 year-end release](https://www.atptour.com/en/news/year-end-pif-atp-rankings-2025-release)
  and [WTA numeric singles ranking PDF](https://wtafiles.wtatennis.com/pdf/rankings/RankingArchive/Singles_Numeric_2025.pdf).
  All 250 WTA rank/point pairs were cross-checked against the official PDF.
  Seven names use shortened or alternative spellings in the PDF; stable source
  identities and exact DOB checks govern birthplace resolution. The original
  200 players retain exactly the same source names, ranks and points. ATP's
  wider ranks come from the attributed machine-readable archive; the release
  is context for the year-end date, rather than a separate verification of all
  250 ATP rows.
- [Wikidata](https://www.wikidata.org/): identity, birthplace, coordinates and
  country. Normalized names must match and source DOB must agree exactly.
  Missing English labels are checked against Wikidata's default multilingual
  labels. The nine documented official-profile birthplace overrides from the
  existing builder retain their source links and verified source identities.
- [WorldPop Global 2 R2025A](https://hub.worldpop.org/project/categories?id=3):
  2025 population estimates from country rasters, **CC BY 4.0**. All three H3
  resolutions are rebuilt from this cohort and include populated reference
  areas. Cached population totals never reuse another cohort's membership.

The dashboard records retrieval dates and SHA-256 hashes of the four CSV
inputs. The checked WTA PDF has SHA-256
`fd3c08227b186f837c63d17f7fe32aa926f927e9fe1d5defbfc9a7ce4bda3278`.

Ranking points are rolling ranking totals, not calendar-year point earnings.
ATP and WTA have separate systems; use the tour filter for point comparisons.
Represented nationality, residence, training base and hometown do not become
birthplaces.

## Coverage and public QA

| Cohort | Players | Mapped birthplaces | Player coverage | Ranking-point coverage |
| --- | ---: | ---: | ---: | ---: |
| ATP | 250 | 236 | 94.4% | 97.9% |
| WTA | 250 | 226 | 90.4% | 95.5% |
| Both tours | 500 | 462 | 92.4% | 96.6% |

The 462 mapped players represent 360 birthplace locations in 65 birth
countries. All 500 players remain in counts, ranking totals, tables and
filters. Unmapped players are excluded from geographic and population rates.

There are 38 unresolved players: 30 identity name/DOB checks, seven missing
birthplace/country/coordinate records, and one known conflicting birthplace.
Ashlyn Krueger remains unresolved because official profile sources disagree
between Springfield, Missouri and Dallas, Texas. A later Wikidata coordinate
does not silently override this conflict.

See the explorer's **About data** tab or the downloadable
[birthplace QA list](data/birthplace_qa.csv) for each unresolved identity.

## Rebuild

```bash
python -m src.ftg.build_tennis_site --limit 250 \
  --output docs/tennis-250/data/dashboard.json

# Repeat at resolutions 1, 2 and 3, with separate output/cache files:
python -m src.ftg.build_population_hexes \
  --input docs/tennis-250/data/dashboard.json \
  --output docs/tennis-250/data/population_hexes_r3.geojson \
  --cache data/cache/tennis_top250_worldpop_2025_r3.json \
  --h3-resolution 3 --use-rasters --include-reference-cells

make catalogs
make test
```

The published top-100 dataset remains separate. Recheck coverage, update this
report and the QA export after a source or birthplace change.
