# NFL data sources

The NFL explorer is a static snapshot of every player with at least one logged
offensive, defensive or special-teams snap in the 2025 regular season.

- Game-level snap counts come from [nflverse](https://github.com/nflverse/nflverse-data/releases/tag/snap_counts), whose files are derived from Pro Football Reference.
- Birth city, state and country fields come from public ESPN athlete profiles.
- Birth-city coordinates are matched conservatively against [GeoNames](https://www.geonames.org/), available under CC BY 4.0. A city is accepted only with a verified country; US cities must also match their state.
- Population-normalized H3 cells at resolutions 1, 2 and 3 use official 1 km 2025 country rasters from [WorldPop Global 2](https://hub.worldpop.org/project/categories?id=3), available under CC BY 4.0. Cells with fewer than two players or fewer than 100,000 residents are visually muted and labelled as unstable.
- Country boundaries use the Natural Earth-derived GeoJSON bundled with the project.
- CARTO and OpenStreetMap provide the base map and are attributed in the map controls.

Birthplace does not imply hometown, high school, college, development pathway or
national identity. Players whose birth city cannot be matched remain visible in
the About data QA queue; the build does not guess coordinates.

No NFL or team logos are included. This independent project is not affiliated
with or endorsed by the NFL, ESPN or Pro Football Reference.
