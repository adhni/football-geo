# Athletics data sources and scope

## Published cohort

This edition contains athletes who recorded an actual start at the **2025 World
Athletics Championships in Tokyo**, held from 13 to 21 September 2025. It covers
all 49 medal events across the women's, men's and mixed programmes.

The build reads the embedded result data from the nine daily pages in the
[official World Athletics results centre](https://worldathletics.org/competition/calendar-results/results/7190593).
The result records provide the World Athletics athlete ID, date of birth,
represented federation, round, placing, mark and relay lineup.

## Participation definitions

- **Athlete:** a person with at least one result other than `DNS`.
- **Event entry:** one athlete in one medal event, regardless of how many rounds
  they contested.
- **Round:** one published result row. For relays, a round is assigned only to
  the four named runners in that lineup.
- **Combined event:** the heptathlon or decathlon is one event entry. Its seven
  or ten component disciplines are not separate entries or rounds here.
- **Medal:** an individual final medal, or a relay medal for every runner named
  in at least one round for that federation. This follows the championship
  participation cohort rather than showing only the four final runners.

`DNS` is excluded because it is not a start. `DNF`, `DQ` and `NM` remain: each
describes an athlete who competed but did not record a finishing mark.

The primary workload is event entries. Rounds are available as a secondary
measure, but should be interpreted carefully because event formats differ.

## Birthplaces

World Athletics athlete IDs are matched to Wikidata property `P1146`. A
birthplace is published only when that identity has a coordinate-bearing place
of birth and country. A conservative fallback accepts an English Wikipedia /
Wikidata title only when its date of birth exactly matches the official result.

Represented federation is never substituted for birthplace. Athletes without a
verified coordinate remain in totals and the public QA queue but do not enter
the birthplace or population maps.

## Population

Population-normalized views use WorldPop Global 2 R2025A constrained 2025
country rasters and H3 cells at resolutions 1–3. The denominator is the full
population of every country raster intersecting a cell. Populated land cells
without a mapped athlete are retained as a faint reference layer; cells with
no resident population are omitted. See the top-level dashboard schema for the
shared GeoJSON contract.

## Rebuild

```bash
python -m src.ftg.build_athletics_site
python -m src.ftg.build_population_hexes --use-rasters --include-reference-cells \
  --input docs/athletics/data/dashboard.json \
  --output docs/athletics/data/population_hexes_r3.geojson \
  --cache data/cache/athletics_worldpop_population_2025.json
```

Repeat the population command with `--h3-resolution 1`, `2` and `3`, changing
the output filename to match.

The World Athletics pages and Wikidata responses are cached under `data/cache/`
and excluded from version control. The published dashboard and H3 layers are
committed so the static site does not depend on live APIs.
