# AFL geography: future improvements

## Current stopping point

The committed 2025 home-and-away snapshot contains 663 players and 9,443
player-games.

- 227 players have a verified birthplace coordinate (34.2% of players; 37.1%
  of player-games).
- 87 additional players have a documented football-origin fallback, producing
  314 mapped players in the combined explorer (47.4% of players; 50.0% of
  player-games).
- 349 players remain in the QA queue.

Birthplace and football origin remain separate fields and labels. Population
normalisation includes verified birthplaces only.

## Recommended next work

1. Complete club-page ground resolution. Many original-team Wikidata items have
   no coordinates, but their Wikipedia pages link to a ground or suburb that
   does. Finish and audit that resolver, recording whether the point represents
   a headquarters, home venue, ground, or administrative area.
2. Add a reviewed origin override table. Store original-team name, canonical
   club, coordinate, precision, source URL, review date, and reviewer note. Use
   it only for recurring clubs that lack structured Wikidata geography.
3. Evaluate official AFL and club player-profile data for explicit birthplace
   or draft-origin fields. Prefer a stable structured feed over page scraping,
   and retain raw response metadata in `data/cache/`.
4. Improve Wikipedia identity matching without relaxing the exact-DOB rule.
   Cache the verified person QID even when geography is missing so future
   rebuilds do not repeat the identity pass.
5. Add QA reports grouped by failure stage: no verified person page, no explicit
   birthplace, no original-team field, original team not linked, club geography
   missing, and ambiguous coordinate.
6. Manually review high-workload unresolved players first. Report both player
   coverage and player-game coverage after every enrichment pass.
7. Browser-test the marker legend and labels at desktop and mobile widths. A
   football-origin point must never appear as a birthplace in a tooltip, table,
   profile, filter, export, or population layer.

## Guardrails

- Never infer birthplace from nationality, hometown, school, junior club, or
  football pathway.
- Use football origin only when an explicit source documents the original team.
- Do not combine football-origin points with birthplace-based population rates.
- Keep unresolved players visible instead of forcing a low-confidence match.

NRL remains deferred until the AFL data contract and QA approach are considered
stable.
