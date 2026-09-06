# AFL data sources

## Scope

The published cohort contains every player row in the 2025 AFL home-and-away season. Finals rows are excluded. Games are player appearances, not estimated time on ground.

## Sources

- Player-game statistics: AFL Tables, accessed through the canonical fitzRoy data release.
- Identity and birthplace: Wikidata, then the explicit `birth_place` field in
  English Wikipedia player infoboxes. Both paths require an exact date-of-birth
  match.
- Football-origin fallback: when no verified birthplace coordinate is available,
  the explicit `originalteam` field in the same DOB-verified Wikipedia player
  infobox is resolved through the original club's Wikidata location, headquarters,
  home venue, or a linked ground/location published on the club page. This is
  labelled `football_origin` and is never represented as a birthplace.
- Population: WorldPop Global 2 R2025A. Population-normalised layers use verified
  birthplaces only; football-origin fallbacks are deliberately excluded.

Raw downloads and query responses are cached locally and are not published. The
dashboard retains source player IDs, location type, provenance, and resolution
precision. Identities without either a defensible birthplace or football-origin
coordinate remain visible in its QA view.
