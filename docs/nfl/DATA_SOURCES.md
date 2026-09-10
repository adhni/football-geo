# NFL data sources

The NFL explorer is a static snapshot of every player with at least one logged
offensive, defensive or special-teams snap in the 2025 regular season.

- Game-level snap counts come from [nflverse](https://github.com/nflverse/nflverse-data/releases/tag/snap_counts), whose files are derived from Pro Football Reference.
- Birth city, state and country fields come from public ESPN athlete profiles.
- College histories and draft fields come from the nflverse player register. For
  map totals, each player is assigned once to the first listed school, which is
  the primary/final program in nflverse's ordered college history. The full
  semicolon-delimited transfer history remains available in the player record.
- College-program locations use the most common 2025 ESPN home-venue city, then
  match that city to GeoNames. Four municipality labels absent from the compact
  GeoNames extract use campus coordinates from the U.S. Department of Education
  College Scorecard. These are program locations, not player birthplaces.
- Birth-city coordinates are matched conservatively against [GeoNames](https://www.geonames.org/), available under CC BY 4.0. A city is accepted only with a verified country; US cities must also match their state.
- Population-normalized H3 cells at resolutions 1, 2 and 3 use official 1 km 2025 country rasters from [WorldPop Global 2](https://hub.worldpop.org/project/categories?id=3), available under CC BY 4.0. Cells with fewer than two players or fewer than 100,000 residents are visually muted and labelled as unstable.
- Country boundaries use the Natural Earth-derived GeoJSON bundled with the project.
- CARTO and OpenStreetMap provide the base map and are attributed in the map controls.

Birthplace does not imply hometown, high school, college, development pathway or
national identity. The birthplace and college lenses are deliberately separate.
Players and programs whose location cannot be matched remain outside mapped
totals; the build does not guess coordinates. Population-normalized modes are
disabled for the college lens because campus location is not a population-rate
denominator for where players were produced.

No NFL or team logos are included. This independent project is not affiliated
with or endorsed by the NFL, ESPN or Pro Football Reference.
