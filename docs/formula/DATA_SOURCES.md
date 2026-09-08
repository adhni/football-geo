# Formula 2025 data notes

## Scope

This edition freezes the completed 2025 Formula 1, FIA Formula 2, FIA Formula 3 and F1 Academy championships. It includes championship races only: Formula 1 Grands Prix and Sprints, Formula 2 and Formula 3 Sprint and Feature Races, and official F1 Academy races. Practice, qualifying, testing and cancelled races are excluded.

The published snapshot contains 90 races, 2,012 driver starts and 56,470 completed racing laps across 106 unique drivers. A driver who started and then retired still receives one start; only completed laps enter the lap total. Drivers who changed teams or crossed series retain separate team and series contributions.

## Classification sources

- Formula 1 classifications come from the 2025 Jolpica F1 API's Ergast-compatible results and sprint feeds. This was used because several FIA archive links for 2025 were stale; the season and race counts were reconciled against the official championship record.
- Formula 2 and Formula 3 use official FIA final-classification HTML pages and PDFs. The cancelled Melbourne Formula 2 Feature Race and Spa Formula 2 Feature Race are not counted.
- F1 Academy uses the official championship results pages for the seven 2025 events.
- Wikipedia championship tables supply full driver names, stable linked identities and final championship points. They are roster/enrichment inputs, not the source of race starts or laps.

Raw responses and retrieval metadata are cached under ignored `data/cache/formula_2025/`. The committed dashboard JSON is reproducible from those snapshots.

## Measures and comparison rules

- **Laps**: completed racing laps summed from final classifications. This is the primary geographic workload measure.
- **Starts**: one appearance in a championship race or sprint, including a retirement after starting.
- **Drivers**: unique drivers after identities are reconciled across teams and series.
- **Wins, podiums and DNFs**: classification-derived profile statistics.
- **Points**: final official championship points, preserved within each series and shown in profiles/tables. Points must not be used to compare workload across series because their scoring rules differ.

## Birthplace resolution and population maps

The builder follows the exact Wikipedia-linked driver identity to Wikidata, then reads date of birth and place of birth. Coordinates come from the birthplace entity, with a parent-place coordinate fallback when the named entity lacks its own coordinate. Nationality, residence, hometown and racing licence country are never substituted for birthplace.

Unresolved or coordinate-less identities remain visible in the QA queue. The snapshot maps 86 of 106 drivers (81.1%) and 52,250 of 56,470 laps (92.5%). Population-normalised layers include verified birthplaces only and use WorldPop 2025 country rasters aggregated into occupied H3 cells at resolutions 1–3.

## Refresh

```bash
python -m src.ftg.build_formula_site --output docs/formula/data/dashboard.json --workers 8
python -m src.ftg.build_population_hexes \
  --input docs/formula/data/dashboard.json \
  --output docs/formula/data/population_hexes_r3.geojson \
  --cache data/cache/formula_worldpop_population_2025_r3.json \
  --h3-resolution 3 --use-rasters
```
