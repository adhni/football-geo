# MLB data sources

The published snapshot covers every player with at least one appearance in the
completed 2025 MLB regular season.

- Team membership, hitting, pitching and player birthplace fields: official
  [MLB Stats API](https://statsapi.mlb.com/api/v1/teams?sportId=1&season=2025&hydrate=division).
- Coordinates: [GeoNames](https://www.geonames.org/) `cities500`, country and
  administrative-code dumps, licensed under CC BY 4.0.
- Population-normalised local areas: [WorldPop](https://www.worldpop.org/)
  2025 country rasters aggregated into H3 cells at resolutions 1, 2 and 3.

Workload is defined as plate appearances plus batters faced. This gives hitters
and pitchers one transparent participation measure without pretending baseball
has a shared minutes statistic. Games are counted once per player-team even
when a position player also pitched. Exact club splits are retained for players
who appeared for more than one team.

Birthplaces are matched only when the recorded city, country and—where
available—state or province agree. Unresolved records remain visible in the QA
queue rather than being assigned to a nearby city.
