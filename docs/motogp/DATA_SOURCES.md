# MotoGP 2025 data notes

## Scope

This edition covers the completed 2025 MotoGP, Moto2, Moto3, MotoE and WorldWCR championships. WorldWCR is presented as a parallel women-only championship, not as a step on the MotoGP development ladder.

The snapshot contains 114 races: 22 MotoGP grands prix, 22 MotoGP sprints, 22 Moto2 races, 22 Moto3 races, 14 MotoE races and 12 WorldWCR races. Practice, qualifying, warm-up, testing, cancelled sessions and riders who did not start are excluded. Retirements count as starts and retain their completed laps.

## Measures

- **Riders:** unique riders with at least one race start.
- **Starts:** one rider appearance in one included race or sprint.
- **Laps:** completed racing laps reported in the official classification.
- **Points, wins and podiums:** profile context only. Points are not compared across series because their scoring systems differ.

The published totals are 163 riders, 2,660 starts and 40,129 completed laps.

## Sources and birthplace resolution

MotoGP, Moto2, Moto3 and MotoE results and rider profiles come from the official MotoGP results service. WorldWCR results and biographical entry lists come from the official WorldSBK resources service.

Birthplaces are resolved conservatively. An exact date-of-birth match to a Wikidata person and coordinate-bearing birthplace is preferred. Otherwise, an official MotoGP birth city or WorldWCR biographical birthplace is matched to an unambiguous GeoNames locality. Sporting nationality is never treated as birthplace or birth country. Ambiguous or unavailable places stay in the public QA queue.

The release maps 147 of 163 riders (90.2%) and 37,649 of 40,129 completed laps (93.8%). Population-normalised layers contain mapped birthplaces only.

## Reproducibility

Raw API responses and official PDFs are cached under ignored `data/cache/motogp_2025/`, alongside retrieval timestamps and hashes. Rebuild with:

```bash
python -m src.ftg.build_motogp_site --output docs/motogp/data/dashboard.json --workers 8
```

Generate each committed WorldPop layer by running `src.ftg.build_population_hexes` with H3 resolutions 1, 2 and 3 and the corresponding MotoGP dashboard input.
