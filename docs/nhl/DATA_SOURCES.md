# NHL data sources

The NHL explorer is a static snapshot of every skater and goalie with at least
one appearance in the 2025–26 regular season.

- Team rosters, exact per-team season totals and recorded player birthplaces come from the NHL's public JSON endpoints. The build retains separate team contributions for every traded player before calculating league-wide totals.
- Birth-city coordinates are matched conservatively against [GeoNames](https://www.geonames.org/), available under CC BY 4.0. Country must match, and province/state is checked when GeoNames provides a corresponding administrative code.
- Population-normalized H3 cells at resolutions 1, 2 and 3 use official 1 km 2025 country rasters from [WorldPop Global 2](https://hub.worldpop.org/project/categories?id=3), available under CC BY 4.0. Cells with fewer than two players or fewer than 100,000 residents are visually muted and labelled as unstable.
- Country boundaries use the Natural Earth-derived GeoJSON bundled with the project.
- CARTO and OpenStreetMap provide the base maps and are attributed in the map controls.

Birthplace does not imply hometown, junior club, development pathway,
nationality or national-team eligibility. A player remains in the About data QA
queue when the recorded location cannot be matched conservatively; the build
does not substitute a nearby city.

No NHL or team logos are included. This independent project is not affiliated
with or endorsed by the NHL or its clubs.
